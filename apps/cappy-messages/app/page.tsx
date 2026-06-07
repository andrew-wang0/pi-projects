import React from "react";

import MessageBoard from "@/components/message-board/MessageBoard";
import { readMessageState } from "@/lib/message-store";

export const dynamic = "force-dynamic";

export default async function Page() {
  const initialState = await readMessageState();
  return <MessageBoard initialState={initialState} />;
}
