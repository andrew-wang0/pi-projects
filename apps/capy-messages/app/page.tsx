import React from "react";

import { readMessageState } from "@/lib/message-store";

import MessageBoard from "./message-board";

export const dynamic = "force-dynamic";

export default async function Page() {
  const initialState = await readMessageState();

  return <MessageBoard initialState={initialState} />;
}
