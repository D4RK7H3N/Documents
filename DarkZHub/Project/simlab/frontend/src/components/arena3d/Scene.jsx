/**
 * 3D scene contents: dark fog, ground disc with a subtle grid, ambient +
 * directional + purple rim lighting, orbit controls.  The swarm and the
 * pesticide cloud render inside; all motion is deterministic (motion.js).
 */
import { useEffect } from "react";
import { Grid, OrbitControls } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import InsectSwarm from "./InsectSwarm.jsx";
import PesticideCloud from "./PesticideCloud.jsx";

function CameraReset({ resetSignal }) {
  const controls = useThree((state) => state.controls);
  useEffect(() => {
    if (controls && resetSignal > 0) controls.reset();
  }, [resetSignal, controls]);
  return null;
}

export default function Scene({
  species,
  parts,
  seed,
  totalDots,
  generationState,
  speed,
  loop,
  total,
  paused,
  machineRef,
  kill,
  particleCount,
  autoRotate,
  resetSignal,
  onGenChange,
  onEnded,
  onFrameTime,
}) {
  return (
    <>
      <color attach="background" args={["#0a0810"]} />
      <fog attach="fog" args={["#0a0810", 18, 46]} />

      <ambientLight intensity={0.35} />
      <directionalLight position={[6, 9, 4]} intensity={1.1} color="#e8e4f3" />
      {/* Soft purple rim light from behind */}
      <directionalLight position={[-7, 4, -9]} intensity={1.4} color="#a78bfa" />

      {/* Ground disc + subtle grid */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <circleGeometry args={[11, 48]} />
        <meshStandardMaterial color="#14111c" roughness={0.9} metalness={0.05} />
      </mesh>
      <Grid
        args={[22, 22]}
        cellSize={1}
        cellThickness={0.6}
        cellColor="#2b2440"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#4a3d6e"
        fadeDistance={34}
        fadeStrength={1.2}
        infiniteGrid={false}
        position={[0, 0.01, 0]}
      />

      <InsectSwarm
        species={species}
        parts={parts}
        seed={seed}
        totalDots={totalDots}
        generationState={generationState}
        speed={speed}
        loop={loop}
        total={total}
        machineRef={machineRef}
        paused={paused}
        onGenChange={onGenChange}
        onEnded={onEnded}
        onFrameTime={onFrameTime}
      />

      <PesticideCloud
        seed={seed}
        kill={kill}
        speed={speed}
        particleCount={particleCount}
        machineRef={machineRef}
      />

      <OrbitControls
        makeDefault
        enablePan
        enableDamping
        autoRotate={autoRotate}
        autoRotateSpeed={0.6}
        minDistance={4}
        maxDistance={32}
        minPolarAngle={0.15}
        maxPolarAngle={Math.PI / 2.05}
        target={[0, 1, 0]}
      />
      <CameraReset resetSignal={resetSignal} />
    </>
  );
}
