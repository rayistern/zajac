import { is, Table } from "drizzle-orm";
import { db } from "./setup";

export async function withTransaction(
  testFn: (tx: Omit<typeof db, "$client">) => Promise<void>,
) {
  await db
    .transaction(async (tx) => {
      await testFn(tx);
      // Rollback happens automatically if we throw
      throw new Error("ROLLBACK");
    })
    .catch((err) => {
      if (err.message !== "ROLLBACK") throw err;
    });
}

export async function clearAll() {
  const schema = await import("../src/schema");
  for (const item of Object.values(schema)) {
    if (is(item, Table)) {
      await db.delete(item);
    }
  }
}
