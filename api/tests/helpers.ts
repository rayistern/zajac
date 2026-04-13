import { is, Table, getTableName, sql } from "drizzle-orm";
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
  const tableNames: string[] = [];
  for (const item of Object.values(schema)) {
    if (is(item, Table)) {
      tableNames.push(getTableName(item as Table));
    }
  }
  if (tableNames.length === 0) return;
  // TRUNCATE with CASCADE handles FK constraints and resets sequences
  const quoted = tableNames.map((n) => `"${n}"`).join(", ");
  await db.execute(sql.raw(`TRUNCATE TABLE ${quoted} RESTART IDENTITY CASCADE`));
}
