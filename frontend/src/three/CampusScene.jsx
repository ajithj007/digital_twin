import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Edges, Html, Line, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { STATUS_META } from "../utils/constants.js";
import { shortName } from "../utils/format.js";
import { layoutRooms } from "./layout.js";

const sceneColor = (status) => (STATUS_META[status] || STATUS_META.no_data).scene;

// ---------------------------------------------------------------- static campus furniture
function Ground() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.06, 15]}>
      <planeGeometry args={[340, 300]} />
      <meshStandardMaterial color="#e3eaf3" />
    </mesh>
  );
}

function PathSegment({ a, b, kind }) {
  const dx = b.x - a.x;
  const dz = b.z - a.z;
  const length = Math.hypot(dx, dz);
  const isRoad = kind === "road";
  return (
    <mesh position={[(a.x + b.x) / 2, isRoad ? 0.02 : 0.05, (a.z + b.z) / 2]} rotation={[0, Math.atan2(dx, dz), 0]}>
      <boxGeometry args={[isRoad ? 5 : 2.4, 0.1, length]} />
      <meshStandardMaterial color={isRoad ? "#98a6b9" : "#c5d0de"} />
    </mesh>
  );
}

function Label({ position, children, small }) {
  return (
    <Html position={position} center distanceFactor={small ? 110 : 150} style={{ pointerEvents: "none" }}>
      <div className={`label3d ${small ? "small" : ""}`}>{children}</div>
    </Html>
  );
}

function Furniture({ navMap }) {
  const nodes = useMemo(() => Object.fromEntries((navMap?.nodes || []).map((n) => [n.key, n])), [navMap]);
  return (
    <group>
      {(navMap?.edges || []).map((e, i) =>
        nodes[e.a] && nodes[e.b] ? <PathSegment key={i} a={nodes[e.a]} b={nodes[e.b]} kind={e.kind} /> : null
      )}
      {/* parking (sample) */}
      <mesh position={[48, 0.03, 100]}>
        <boxGeometry args={[40, 0.06, 28]} />
        <meshStandardMaterial color="#cbd5e1" />
      </mesh>
      <Label position={[48, 2, 100]} small>Parking</Label>
      {/* main gate (sample) */}
      <mesh position={[-5, 3, 125]}><boxGeometry args={[1.2, 6, 1.2]} /><meshStandardMaterial color="#475569" /></mesh>
      <mesh position={[5, 3, 125]}><boxGeometry args={[1.2, 6, 1.2]} /><meshStandardMaterial color="#475569" /></mesh>
      <mesh position={[0, 6.2, 125]}><boxGeometry args={[11.5, 0.9, 1.2]} /><meshStandardMaterial color="#1d4ed8" /></mesh>
      <Label position={[0, 11, 125]}>Main Gate</Label>
    </group>
  );
}

// ---------------------------------------------------------------- buildings
function BuildingBlock({ b, selected, dimmed, onSelect, interactive }) {
  const [hover, setHover] = useState(false);
  useEffect(() => {
    document.body.style.cursor = hover && interactive ? "pointer" : "auto";
    return () => { document.body.style.cursor = "auto"; };
  }, [hover, interactive]);
  return (
    <group position={[b.x, 0, b.z]}>
      <mesh
        position={[0, b.height / 2, 0]}
        onClick={(e) => { if (!interactive) return; e.stopPropagation(); onSelect?.(b); }}
        onPointerOver={(e) => { e.stopPropagation(); setHover(true); }}
        onPointerOut={() => setHover(false)}
      >
        <boxGeometry args={[b.width, b.height, b.depth]} />
        <meshStandardMaterial color={selected ? "#93c5fd" : hover ? "#bcd0ea" : "#d3dbe8"} transparent opacity={dimmed ? 0.25 : 1} />
        <Edges color={selected ? "#1d4ed8" : "#64748b"} />
      </mesh>
      {/* roof slab shows the building status colour */}
      <mesh position={[0, b.height + 0.45, 0]}>
        <boxGeometry args={[b.width * 0.94, 0.9, b.depth * 0.94]} />
        <meshStandardMaterial color={sceneColor(b.status)} transparent opacity={dimmed ? 0.3 : 1} />
      </mesh>
      {!dimmed && <Label position={[0, b.height + 7, 0]}>{shortName(b.name)}</Label>}
    </group>
  );
}

function RoomBlocks({ building, floor, fh, selectedRoomId, onSelectRoom, interactive }) {
  const slots = useMemo(() => layoutRooms(floor.rooms.length, building.width, building.depth), [floor, building]);
  const baseY = floor.level * fh + 0.4;
  const h = Math.max(1.6, fh - 1.2);
  return (
    <group>
      {floor.rooms.map((room, i) => {
        const s = slots[i];
        const isSel = room.id === selectedRoomId;
        return (
          <group key={room.id} position={[s.x, baseY + h / 2, s.z]}>
            <mesh onClick={(e) => { if (!interactive) return; e.stopPropagation(); onSelectRoom?.(room); }}>
              <boxGeometry args={[s.w, h, s.d]} />
              <meshStandardMaterial color={sceneColor(room.status)} transparent opacity={isSel ? 1 : 0.78} emissive={isSel ? "#1d4ed8" : "#000000"} emissiveIntensity={isSel ? 0.35 : 0} />
              <Edges color={isSel ? "#1d4ed8" : "#475569"} />
            </mesh>
            <Label position={[0, h / 2 + 1.5, 0]} small>{room.code}</Label>
          </group>
        );
      })}
    </group>
  );
}

function FloorStack({ detail, selectedFloorId, selectedRoomId, onSelectFloor, onSelectRoom, interactive }) {
  const fh = detail.height / detail.floors.length;
  const hasFloor = selectedFloorId != null;
  return (
    <group position={[detail.x, 0, detail.z]}>
      {detail.floors.map((f) => {
        const isSel = f.id === selectedFloorId;
        const y = f.level * fh;
        return (
          <group key={f.id}>
            {isSel ? (
              <>
                <mesh position={[0, y + 0.2, 0]}>
                  <boxGeometry args={[detail.width, 0.4, detail.depth]} />
                  <meshStandardMaterial color="#bfdbfe" />
                </mesh>
                <mesh position={[0, y + fh / 2, 0]}>
                  <boxGeometry args={[detail.width, fh - 0.25, detail.depth]} />
                  <meshBasicMaterial transparent opacity={0} />
                  <Edges color="#1d4ed8" />
                </mesh>
                <RoomBlocks building={detail} floor={f} fh={fh} selectedRoomId={selectedRoomId} onSelectRoom={onSelectRoom} interactive={interactive} />
              </>
            ) : (
              <mesh position={[0, y + fh / 2, 0]} onClick={(e) => { if (!interactive) return; e.stopPropagation(); onSelectFloor?.(f); }}>
                <boxGeometry args={[detail.width, fh - 0.25, detail.depth]} />
                <meshStandardMaterial color="#d3dbe8" transparent opacity={hasFloor ? 0.1 : 0.92} depthWrite={!hasFloor} />
                <Edges color={sceneColor(f.status)} />
              </mesh>
            )}
            <Label position={[detail.width / 2 + 5, y + fh / 2, 0]} small>{f.name}</Label>
          </group>
        );
      })}
    </group>
  );
}

// ---------------------------------------------------------------- overlays
function HighlightRing({ building }) {
  const ref = useRef();
  useFrame(({ clock }) => {
    if (ref.current) ref.current.scale.setScalar(1 + 0.08 * Math.sin(clock.elapsedTime * 4));
  });
  const r = Math.max(building.width, building.depth) / 2 + 5;
  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[building.x, 0.35, building.z]}>
      <ringGeometry args={[r, r + 2.2, 56]} />
      <meshBasicMaterial color="#dc2626" side={THREE.DoubleSide} transparent opacity={0.85} />
    </mesh>
  );
}

function RouteOverlay({ route }) {
  if (!route || route.length < 2) return null;
  const pts = route.map((p) => [p.x, 0.8, p.z]);
  const end = route[route.length - 1];
  const start = route[0];
  return (
    <group>
      <Line points={pts} color="#2563eb" lineWidth={5} />
      <mesh position={[start.x, 1.6, start.z]}><sphereGeometry args={[2.2, 16, 16]} /><meshStandardMaterial color="#16a34a" /></mesh>
      <mesh position={[end.x, 5, end.z]} rotation={[Math.PI, 0, 0]}><coneGeometry args={[2.6, 6, 16]} /><meshStandardMaterial color="#dc2626" /></mesh>
    </group>
  );
}

// ---------------------------------------------------------------- camera
function CameraRig({ focus }) {
  const controls = useRef();
  const { camera } = useThree();
  const animating = useRef(true);
  const goal = useRef({ position: new THREE.Vector3(), target: new THREE.Vector3() });
  const key = JSON.stringify(focus);

  useEffect(() => {
    goal.current.position.set(...focus.position);
    goal.current.target.set(...focus.target);
    animating.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useFrame(() => {
    if (!animating.current || !controls.current) return;
    camera.position.lerp(goal.current.position, 0.08);
    controls.current.target.lerp(goal.current.target, 0.08);
    controls.current.update();
    if (camera.position.distanceTo(goal.current.position) < 0.5) animating.current = false;
  });

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enableDamping
      maxPolarAngle={Math.PI / 2.05}
      minDistance={15}
      maxDistance={420}
      onStart={() => { animating.current = false; }}
    />
  );
}

function computeFocus(selected, floor) {
  if (!selected) return { target: [0, 0, 20], position: [0, 190, 260] };
  const size = Math.max(selected.width, selected.depth);
  if (floor) {
    const fh = selected.height / selected.floors.length;
    return { target: [selected.x, floor.level * fh, selected.z], position: [selected.x, floor.level * fh + size * 0.85, selected.z + size * 0.8] };
  }
  return { target: [selected.x, selected.height / 2, selected.z], position: [selected.x + 8, selected.height + size * 0.9, selected.z + size * 1.15 + 20] };
}

// ---------------------------------------------------------------- main component
/**
 * Props
 *  buildings            list from GET /buildings (position, size, status)
 *  detail               GET /buildings/{id} for the selected building (floors + rooms)
 *  selectedBuildingId / selectedFloorId / selectedRoomId
 *  highlightBuildingId  draws a pulsing ring (used when an incident is opened from the incident list)
 *  route                [{x, z}] polyline from the navigation API
 *  navMap               roads and walkways from GET /navigation/map
 *  interactive          false = preview only (dashboard)
 */
export default function CampusScene({
  buildings = [], detail = null, navMap = null, selectedBuildingId = null, selectedFloorId = null, selectedRoomId = null,
  highlightBuildingId = null, route = null, onSelectBuilding, onSelectFloor, onSelectRoom, interactive = true, height = 560,
}) {
  const selected = buildings.find((b) => b.id === selectedBuildingId) || null;
  const showDetail = detail && selected && detail.id === selected.id;
  const floor = showDetail ? detail.floors.find((f) => f.id === selectedFloorId) : null;
  const focus = computeFocus(showDetail ? detail : selected, floor);
  const highlighted = buildings.find((b) => b.id === highlightBuildingId);

  return (
    <div className="scene-canvas" style={{ height }}>
      <Canvas camera={{ position: [0, 190, 260], fov: 45, near: 0.5, far: 2500 }} dpr={[1, 2]}>
        <color attach="background" args={["#f4f7fb"]} />
        <ambientLight intensity={0.85} />
        <directionalLight position={[120, 220, 140]} intensity={1.05} />
        <Ground />
        <Furniture navMap={navMap} />
        {buildings.map((b) =>
          showDetail && b.id === selected.id ? null : (
            <BuildingBlock key={b.id} b={b} selected={b.id === selectedBuildingId} dimmed={!!selected && b.id !== selectedBuildingId} onSelect={onSelectBuilding} interactive={interactive} />
          )
        )}
        {showDetail && (
          <FloorStack detail={detail} selectedFloorId={selectedFloorId} selectedRoomId={selectedRoomId} onSelectFloor={onSelectFloor} onSelectRoom={onSelectRoom} interactive={interactive} />
        )}
        {highlighted && <HighlightRing building={highlighted} />}
        <RouteOverlay route={route} />
        <CameraRig focus={focus} />
      </Canvas>
    </div>
  );
}
