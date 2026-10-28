import { createContext, useContext } from "react";

/** Holds GET /api/meta (is the data simulated? is the simulator running?). */
export const MetaContext = createContext(null);
export const useMeta = () => useContext(MetaContext);
