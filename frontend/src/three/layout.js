// Shared helper: positions of rooms inside a building footprint (used by the 3D scene AND the 2D floor plan,
// so both show the rooms in the same order). The floor layout is SCHEMATIC - it is not a surveyed floor plan.
export function layoutRooms(count, width, depth) {
  const rows = count <= 3 ? 1 : 2;
  const cols = Math.ceil(count / rows);
  const cellW = (width - 2) / cols;
  const cellD = (depth - 2) / rows;
  return Array.from({ length: count }, (_, i) => {
    const row = Math.floor(i / cols);
    const col = i % cols;
    return {
      x: -width / 2 + 1 + cellW * (col + 0.5),
      z: -depth / 2 + 1 + cellD * (row + 0.5),
      w: cellW - 0.8,
      d: cellD - 0.8,
      row,
      col,
      cols,
    };
  });
}
