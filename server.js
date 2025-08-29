import express from "express";
import basicAuth from "express-basic-auth";
import { Low } from "lowdb";
import { JSONFile } from "lowdb/node";

const adapter = new JSONFile("db.json");
const db = new Low(adapter, { logs: [], feedback: {} });
await db.read();

const app = express();
app.use(express.json());
app.use(basicAuth({ users: { admin: "password123" }, challenge: true }));

app.get("/admin/logs", async (req, res) => {
  await db.read();
  res.json(db.data.logs.slice(-50));
});

app.get("/admin/tasks", (req, res) => {
  res.json({ tasks: db.data.tasks || {} });
});

app.listen(3000, () => console.log("Dashboard running at http://localhost:3000/admin/logs"));
