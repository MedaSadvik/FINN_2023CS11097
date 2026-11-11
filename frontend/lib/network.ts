import raw from "@/data/network.json";
import type { Network } from "./types";

/** The synthetic network used for signed-out visitors and as the sample contacts. */
export const demoNetwork = raw as unknown as Network;
export * from "./network-core";
