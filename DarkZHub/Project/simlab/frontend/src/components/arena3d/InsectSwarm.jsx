/**
 * InstancedMesh insect swarm for the 3D evolution view.
 *
 * One InstancedMesh per body-part group (body, legs, wings, eyes) -- a
 * handful of draw calls total, never 400 separate meshes.  Per-instance
 * color (instanceColor) carries the resistant/normal state; matrices come
 * from the shared deterministic motion so the same seed + generation +
 * index always renders the same pose.
 *
 * Per-generation data (who is purple, who survives, who dies) is computed
 * by the SHARED pure functions in evolutionLogic.js -- no duplicated
 * simulation logic here.  Phase timing comes from phaseClock.js, shared
 * with the 2D arena.
 */
import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { insectPose } from "./motion.js";
import { phaseAt, phaseDuration } from "../phaseClock.js";

const COLOR_RESISTANT = new THREE.Color("#a78bfa");
const COLOR_NORMAL = new THREE.Color("#7d7590");
const COLOR_WHITE = new THREE.Color("#efe9ff");
const COLOR_MUTANT = new THREE.Color("#c9b6ff");

const easeOutBack = (t) => 1 + 2.7 * Math.pow(t - 1, 3) + 1.7 * Math.pow(t - 1, 2);
const clamp01 = (t) => Math.max(0, Math.min(1, t));

export default function InsectSwarm({
  species,
  parts,
  seed,
  totalDots,
  generationState,
  speed,
  loop,
  total,
  machineRef, // {genIndex, phaseIndex, t, genTime} owned by the parent
  onGenChange,
  onEnded,
  onFrameTime,
  paused = false,
}) {
  const meshesRef = useRef([]); // [{mesh, part, capacity, perInsect}]
  const scratch = useMemo(
    () => ({ dummy: new THREE.Object3D(), color: new THREE.Color(), base: new THREE.Color() }),
    []
  );

  const instanceCount = Math.min(totalDots, species.instanceCap ?? totalDots);

  // (Generation sync on scrub is owned by the parent via machineRef.)

  // New experiment: rewind everything.
  useEffect(() => {
    machineRef.current = { genIndex: 0, phaseIndex: 0, t: 0, genTime: 0 };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed, total]);

  // Explicit disposal of geometries, materials and instance buffers.
  // Captures the CURRENT mesh list so a quality change disposes the
  // previous generation of meshes, and unmount disposes the last one.
  useEffect(() => {
    const meshes = [...meshesRef.current];
    return () => {
      for (const { mesh } of meshes) {
        mesh.geometry?.dispose();
        mesh.material?.dispose();
        mesh.instanceColor?.dispose?.();
        mesh.dispose?.();
      }
    };
  }, [parts, species, instanceCount]);

  useFrame((state, delta) => {
    const dt = Math.min(0.1, delta);
    const m = machineRef.current;
    if (!paused) {
      m.genTime += dt;
      let guard = 0;
      while (guard++ < 12) {
        const dur = phaseDuration(m.phaseIndex, speed);
        if (m.t < dur) break;
        m.t -= dur;
        m.phaseIndex += 1;
        if (m.phaseIndex < 3) continue;
        m.phaseIndex = 0;
        m.genTime = 0;
        if (m.genIndex + 1 >= total && !loop) {
          // Park on the final generation and tell the parent to pause.
          m.phaseIndex = 2;
          m.t = phaseDuration(2, speed);
          onEnded?.();
          break;
        }
        m.genIndex = loop ? (m.genIndex + 1) % total : m.genIndex + 1;
        onGenChange?.(m.genIndex);
      }
    }
    const t0 = performance.now();
    renderInstances(m);
    onFrameTime?.(performance.now() - t0);
  });

  function renderInstances(m) {
    const st = generationState;
    if (!st || meshesRef.current.length === 0) return;
    const { phase, p01, fast } = phaseAt(m.t, speed);
    const genIndex = Math.min(m.genIndex, total - 1);
    const { dummy, color, base } = scratch;

    for (const entry of meshesRef.current) {
      const { mesh, part, perInsect } = entry;
      let idx = 0;

      for (let i = 0; i < instanceCount; i++) {
        const pose = insectPose(seed, genIndex, i, m.genTime, species);
        const isSurvivor = st.survivorSet.has(i);
        const incomingPurple = st.incomingColored.has(i);
        const postPurple = st.postColored.has(i);
        let scale = species.scale;
        let y = pose.y;
        let tumbleX = 0;

        if (fast) {
          // High speeds: skip sub-animations, crossfade the colors only.
          base.copy(incomingPurple ? COLOR_RESISTANT : COLOR_NORMAL).lerp(
            postPurple ? COLOR_RESISTANT : COLOR_NORMAL,
            p01
          );
          if (st.survCounts.total === 0 && p01 > 0.5) scale *= 1 - (p01 - 0.5) * 2;
        } else if (phase === "selection" && !isSurvivor) {
          // Dies: tumble belly-up, fall to the ground, shrink out.
          y = THREE.MathUtils.lerp(pose.y, 0.06, p01 * p01);
          tumbleX = Math.PI * p01;
          if (p01 > 0.55) scale *= Math.max(0.001, 1 - (p01 - 0.55) / 0.45);
          base.copy(incomingPurple ? COLOR_RESISTANT : COLOR_NORMAL);
        } else if (phase === "reproduction" && !isSurvivor) {
          // Offspring pop in with the post-mutation color; new mutants sparkle.
          const delay = (((i * 13) % 17) / 17) * 0.55;
          const grow = clamp01((p01 - delay) / 0.45);
          scale *= Math.max(0.001, easeOutBack(grow));
          const mutant = postPurple && !incomingPurple;
          color.copy(mutant ? COLOR_MUTANT : postPurple ? COLOR_RESISTANT : COLOR_NORMAL);
          if (mutant && grow > 0.2 && grow < 0.95) {
            color.lerp(COLOR_WHITE, 0.6 * (1 - grow)); // sparkle flash
          }
          base.copy(color);
        } else if (phase === "selection" && isSurvivor && incomingPurple) {
          // Surviving resistant insects pulse a faint purple glow.
          const pulse = 0.5 + 0.5 * Math.sin(p01 * Math.PI * 4);
          base.copy(COLOR_RESISTANT).lerp(COLOR_WHITE, 0.22 * pulse);
        } else {
          base.copy(incomingPurple ? COLOR_RESISTANT : COLOR_NORMAL);
        }

        if (part.mode === "instance") {
          for (let k = 0; k < perInsect; k++) {
            mesh.instanceColor.setXYZ(idx + k, base.r, base.g, base.b);
          }
        }

        if (part.name === "legs") {
          for (let k = 0; k < perInsect; k++) {
            const side = k % 2 === 0 ? 1 : -1;
            dummy.position.set(pose.x, y + 0.02 * species.scale, pose.z);
            dummy.rotation.set(tumbleX, pose.heading, pose.legSwing * 0.35 * side);
            dummy.scale.setScalar(scale);
            dummy.updateMatrix();
            mesh.setMatrixAt(idx++, dummy.matrix);
          }
        } else if (part.name === "wings") {
          for (let k = 0; k < perInsect; k++) {
            const side = k % 2 === 0 ? 1 : -1;
            dummy.position.set(pose.x, y + 0.1 * species.scale, pose.z);
            dummy.rotation.set(tumbleX, pose.heading, pose.flapAngle * 0.6 * side);
            dummy.scale.setScalar(scale);
            dummy.updateMatrix();
            mesh.setMatrixAt(idx++, dummy.matrix);
          }
        } else {
          dummy.position.set(pose.x, y, pose.z);
          dummy.rotation.set(tumbleX, pose.heading, 0);
          dummy.scale.setScalar(scale);
          dummy.updateMatrix();
          mesh.setMatrixAt(idx++, dummy.matrix);
        }
      }

      mesh.count = idx;
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    }
  }

  const meshes = useMemo(() => {
    meshesRef.current = [];
    return parts.map((part) => {
      const perInsect =
        part.name === "legs"
          ? species.legCount
          : part.name === "wings"
            ? species.wingCount
            : 1;
      const capacity = Math.max(1, instanceCount * perInsect);
      const material = new THREE.MeshStandardMaterial({
        color: part.mode === "fixed" ? part.color : "#ffffff",
        transparent: part.opacity != null && part.opacity < 1,
        opacity: part.opacity ?? 1,
        roughness: 0.55,
        metalness: 0.1,
        emissive: new THREE.Color(part.mode === "instance" ? "#2c2140" : "#000000"),
        emissiveIntensity: part.mode === "instance" ? 0.5 : 0,
      });
      const mesh = new THREE.InstancedMesh(part.geometry, material, capacity);
      mesh.instanceColor = new THREE.InstancedBufferAttribute(
        new Float32Array(capacity * 3).fill(1),
        3
      );
      mesh.frustumCulled = false;
      meshesRef.current.push({ mesh, part, capacity, perInsect });
      return <primitive key={part.name} object={mesh} />;
    });
    // Rebuild when the species or quality cap changes; dispose runs in the
    // effect above (keyed on the same inputs).
  }, [parts, species, instanceCount]);

  return <group>{meshes}</group>;
}
