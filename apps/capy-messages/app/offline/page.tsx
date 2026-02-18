import React from "react";

export default function OfflinePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center p-8 text-center">
      <h1 className="text-3xl font-bold">You are offline</h1>
      <p className="mt-4 text-base text-gray-600">
        Reconnect to load the latest Capybara messages.
      </p>
    </main>
  );
}
