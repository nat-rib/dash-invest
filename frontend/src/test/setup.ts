import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// O Testing Library só registra cleanup automático quando afterEach é global;
// como usamos imports explícitos, registramos aqui.
afterEach(cleanup);
