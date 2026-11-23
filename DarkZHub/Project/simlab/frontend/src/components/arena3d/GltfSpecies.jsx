/**
 * glb species loading path (dormant: no model files are committed).
 *
 * Loads a .glb with useGLTF and converts its meshes into swarm parts by
 * name (body/leg/wing prefixes).  Any failure -- missing file, malformed
 * glb -- propagates to ModelLoadErrorBoundary in Arena3D, which falls
 * back to the procedural builder for that species.
 *
 * README: any committed model must be CC0 or CC-BY (with attribution).
 */
import { useMemo } from "react";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { useGLTF } from "@react-three/drei";
import Scene from "./Scene.jsx";

function partNameFor(meshName) {
  const n = (meshName ?? "").toLowerCase();
  if (n.includes("leg")) return "legs";
  if (n.includes("wing")) return "wings";
  return "body";
}

function partsFromGltf(scene) {
  const byName = new Map();
  scene.updateMatrixWorld(true);
  scene.traverse((child) => {
    if (!child.isMesh || !child.geometry) return;
    const name = partNameFor(child.name);
    const geometry = child.geometry.clone();
    geometry.applyMatrix4(child.matrixWorld);
    const list = byName.get(name) ?? [];
    list.push(geometry);
    byName.set(name, list);
  });
  if (!byName.has("body")) throw new Error("glb has no body mesh");
  const parts = [];
  for (const [name, geometries] of byName) {
    parts.push({
      name,
      geometry: mergeGeometries(geometries, false),
      mode: name === "wings" ? "fixed" : "instance",
      color: name === "wings" ? "#d8d2e8" : undefined,
      opacity: name === "wings" ? 0.55 : undefined,
    });
    for (const g of geometries) g.dispose();
  }
  return parts;
}

export default function GltfSpecies({ url, sceneProps, fallbackParts }) {
  const { scene } = useGLTF(url);
  const parts = useMemo(() => partsFromGltf(scene), [scene]);
  return <Scene {...sceneProps} parts={parts ?? fallbackParts} />;
}
