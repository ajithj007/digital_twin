import { useState } from "react";

/** Shows /asiet-logo.png if the team adds it to frontend/public, otherwise a simple text mark. */
export default function Logo({ size = 40 }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="logo-mark" style={{ width: size, height: size, fontSize: size * 0.3 }}>ASIET</div>
    );
  }
  return <img src="/asiet-logo.png" alt="ASIET logo" width={size} height={size} onError={() => setFailed(true)} style={{ objectFit: "contain" }} />;
}
