/**
 * Drifting pesticide cloud: instanced billboard sprites.
 * Density scales with pesticide_kill from the experiment params; phase
 * progress comes from the shared machine ref (no per-frame re-renders).
 */
import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { generationSeed, mulberry32 } from "../evolutionLogic.js";
import { phaseAt } from "../phaseClock.js";
import { ARENA } from "./motion.js";

export default function PesticideCloud({ seed, kill, speed, particleCount, machineRef }) {
  const meshRef = useRef(null);
  const count = Math.max(8, Math.round(particleCount * Math.min(1, Math.max(0.15, kill))));

  const particles = useMemo(() => {
    const rng = mulberry32((generationSeed(seed, 0) * 31 + 7) >>> 0);
    return Array.from({ length: count }, () => ({
      x: (rng() * 2 - 1) * ARENA.radius,
      z: (rng() * 2 - 1) * ARENA.radius,
      y: 0.6 + rng() * (ARENA.ceiling + 1),
      drift: 0.4 + rng() * 0.8,
      phase: rng() * Math.PI * 2,
      size: 1.6 + rng() * 2.6,
    }));
  }, [seed, count]);

  const geometry = useMemo(() => new THREE.PlaneGeometry(1, 1), []);
  const material = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: "#8c987e",
        transparent: true,
        opacity: 0.16 + 0.2 * Math.min(1, kill),
        depthWrite: false,
        side: THREE.DoubleSide,
      }),
    [kill]
  );

  useEffect(
    () => () => {
      geometry.dispose();
      material.dispose();
      meshRef.current?.dispose?.();
    },
    [geometry, material]
  );

  useFrame(({ camera }) => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const { phase, p01 } = phaseAt(machineRef.current.t, speed);
    if (phase !== "spray") {
      mesh.count = 0;
      return;
    }
    const dummy = new THREE.Object3D();
    const t = p01;
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      const drift = (t - 0.5) * 14 * p.drift;
      dummy.position.set(
        p.x + drift,
        p.y + Math.sin(p.phase + t * 3) * 0.4,
        p.z + Math.cos(p.phase * 1.3 + t * 2.2) * 1.2
      );
      dummy.quaternion.copy(camera.quaternion); // billboard
      dummy.scale.setScalar(p.size);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.count = particles.length;
    mesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, material, Math.max(1, count)]}
      frustumCulled={false}
    />
  );
}
