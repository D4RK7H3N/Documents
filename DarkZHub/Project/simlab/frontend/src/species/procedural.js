/**
 * Procedural species body builders.
 *
 * Each builder composes three.js primitives (spheres, capsules, cones,
 * thin boxes) into ONE merged BufferGeometry per body-part group so the
 * whole species can be drawn with a handful of InstancedMesh draw calls.
 * Insects face +Z; the swarm applies heading as a Y rotation.
 */
import {
  BoxGeometry,
  CapsuleGeometry,
  ConeGeometry,
  CylinderGeometry,
  SphereGeometry,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

function place(geometry, { x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1 } = {}) {
  geometry.rotateX(rx);
  geometry.rotateY(ry);
  geometry.rotateZ(rz);
  geometry.scale(sx, sy, sz);
  geometry.translate(x, y, z);
  return geometry;
}

function sphere(radius, opts) {
  return place(new SphereGeometry(radius, 10, 8), opts);
}

function capsule(radius, length, opts) {
  return place(new CapsuleGeometry(radius, length, 4, 8), opts);
}

function cone(radius, height, opts) {
  return place(new ConeGeometry(radius, height, 8), opts);
}

function thinBox(w, h, d, opts) {
  return place(new BoxGeometry(w, h, d), opts);
}

function cylinder(radius, height, opts) {
  return place(new CylinderGeometry(radius, radius, height, 8), opts);
}

function merge(list) {
  const merged = mergeGeometries(list, false);
  if (!merged) throw new Error("mergeGeometries returned null");
  for (const g of list) g.dispose();
  return merged;
}

/** Six legs as one merged geometry (for body-attached legs). */
function legPairSet(len, radius, { spread = 0.16, droop = 0.5, zOffsets = [-0.12, 0.02, 0.16] } = {}) {
  const legs = [];
  for (const side of [-1, 1]) {
    for (const z of zOffsets) {
      legs.push(
        thinBox(radius * 2, len, radius * 2, {
          x: side * spread,
          y: -len / 2 + droop * 0.15,
          z,
          rz: side * droop,
        })
      );
    }
  }
  return merge(legs);
}

/**
 * Every builder returns { parts } where each part is
 * { name, geometry, mode: "instance" | "fixed", color, opacity }.
 * "instance" parts take the per-insect instanceColor (resistant/normal);
 * "fixed" parts keep their own material color (eyes, translucent wings).
 */

export function buildMosquito() {
  const body = merge([
    capsule(0.045, 0.42, { rx: Math.PI / 2, z: -0.16, sy: 1.15 }), // abdomen
    sphere(0.085, { z: 0.1, y: 0.02 }), // thorax
    sphere(0.055, { z: 0.21 }), // head
    cone(0.012, 0.22, { rx: Math.PI / 2, z: 0.32 }), // proboscis
  ]);
  return {
    parts: [
      { name: "body", geometry: body, mode: "instance" },
      {
        name: "legs",
        geometry: legPairSet(0.42, 0.008, { spread: 0.13, droop: 0.85, zOffsets: [-0.14, 0.02, 0.14] }),
        mode: "instance",
      },
      {
        name: "wings",
        geometry: merge([thinBox(0.3, 0.006, 0.09, { x: 0.16, y: 0.09, z: 0.06, rz: 0.25 })]),
        mode: "fixed",
        color: "#d8d2e8",
        opacity: 0.55,
      },
    ],
  };
}

export function buildBeetle() {
  const body = merge([
    sphere(0.26, { sy: 0.62, sz: 1.25, z: -0.05, y: 0.16 }), // elytra shell
    sphere(0.14, { z: 0.26, y: 0.12 }), // head
    thinBox(0.02, 0.02, 0.1, { z: 0.4, y: 0.1 }), // horn hint
  ]);
  return {
    parts: [
      { name: "body", geometry: body, mode: "instance" },
      {
        name: "legs",
        geometry: legPairSet(0.22, 0.02, { spread: 0.24, droop: 0.75, zOffsets: [-0.18, 0.02, 0.18] }),
        mode: "instance",
      },
    ],
  };
}

export function buildFruitFly() {
  const body = merge([
    capsule(0.06, 0.22, { rx: Math.PI / 2, z: -0.06, sy: 1.1 }), // abdomen
    sphere(0.085, { z: 0.14, y: 0.03 }), // thorax+head mass
  ]);
  const eyes = merge([
    sphere(0.035, { x: 0.055, z: 0.2, y: 0.04 }),
    sphere(0.035, { x: -0.055, z: 0.2, y: 0.04 }),
  ]);
  return {
    parts: [
      { name: "body", geometry: body, mode: "instance" },
      { name: "eyes", geometry: eyes, mode: "fixed", color: "#c2413b" },
      {
        name: "legs",
        geometry: legPairSet(0.18, 0.01, { spread: 0.12, droop: 0.8, zOffsets: [-0.1, 0.04, 0.14] }),
        mode: "instance",
      },
      {
        name: "wings",
        geometry: merge([sphere(0.11, { sx: 1.4, sy: 0.12, x: 0.14, y: 0.12, z: 0.02 })]),
        mode: "fixed",
        color: "#e4ddf0",
        opacity: 0.5,
      },
    ],
  };
}

const BUILDERS = {
  mosquito: buildMosquito,
  beetle: buildBeetle,
  fruit_fly: buildFruitFly,
};

/** Build the part geometries for a species id, or null if procedural-only. */
export function buildProceduralParts(speciesId) {
  const builder = BUILDERS[speciesId];
  return builder ? builder().parts : null;
}

/** Wing geometry needs mirroring for the second wing; helper for the swarm. */
export { cylinder };
