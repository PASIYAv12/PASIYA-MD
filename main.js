/**
 * PasiduAgent - WhatsApp persona-driven agent (Baileys)
 * - admin-only commands: /run, /confirm_run, /status
 * - scheduled tasks via cron (persona.json)
 * - dry-run mode
 *
 * WARNING: keep .env out of git
 */

const { default: makeWASocket, DisconnectReason, useSingleFileAuthState, fetchLatestBaileysVersion } = require('@adiwajshing/baileys');
const pino = require('pino');
const { Boom } = require('@hapi/boom');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');
const cron = require('node-cron');
const { Low, JSONFile } = require('lowdb');

dotenv.config();

const logger = pino({ level: 'info' });
const MODE = process.env.MODE || 'dryrun';
const ADMIN_WHITELIST = (process.env.ADMIN_WHITELIST || '').split(',').map(s => s.trim()).filter(Boolean);
const BOT_NAME = process.env.BOT_NAME || 'PasiduAgent';

const personaPath = path.join(__dirname, 'persona.json');
const persona = JSON.parse(fs.readFileSync(personaPath, 'utf8'));

// Simple lowdb for logs and session metadata
const dbFile = path.join(__dirname, 'db.json');
const adapter = new JSONFile(dbFile);
const db = new Low(adapter);

async function initDB() {
  await db.read();
  db.data ||= { logs: [], runCount: 0 };
  await db.write();
}

function appendLog(entry) {
  db.data.logs.push({ ts: new Date().toISOString(), ...entry });
  db.write().catch(console.error);
}

function replyPrefix() {
  return persona.style?.reply_prefix || '';
}

// auth state saved to file
const authFile = path.join(__dirname, 'auth_info_multi.json');
const { state, saveState } = useSingleFileAuthState(authFile);

async function startSock() {
  await initDB();
  const { version } = await fetchLatestBaileysVersion();
  logger.info({ version }, 'using baileys version');

  const sock = makeWASocket({
    logger,
    printQRInTerminal: true,
    auth: state,
    version
  });

  sock.ev.on('creds.update', saveState);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect } = update;
    if (connection === 'close') {
      const reason = (lastDisconnect?.error) ? new Boom(lastDisconnect.error)?.output?.statusCode : null;
      logger.warn('connection closed', { reason });
      // reconnect on non-intentional disconnect
      if (lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut) {
        startSock();
      } else {
        logger.info('Logged out — delete auth and restart scan');
      }
    } else if (connection === 'open') {
      logger.info('connection opened');
    }
  });

  // message handler
  sock.ev.on('messages.upsert', async m => {
    try {
      const messages = m.messages;
      for (const msg of messages) {
        if (!msg.message) continue;
        const msgType = Object.keys(msg.message)[0];
        const sender = msg.key.remoteJid;
        // only handle direct chat (not groups) for admin commands in this simple demo
        const isGroup = sender.endsWith('@g.us');
        const from = isGroup ? sender : sender; // for now we treat both similarly
        const pushName = msg.pushName || 'unknown';
        let text = '';

        if (msgType === 'conversation') text = msg.message.conversation;
        else if (msgType === 'extendedTextMessage') text = msg.message.extendedTextMessage.text;
        else continue;

        logger.info({ from, text }, 'received message');

        // simple admin check by sender phone number (jid looks like '94722986772@s.whatsapp.net')
        const phone = from.split('@')[0];
        const isAdmin = ADMIN_WHITELIST.includes('+' + phone) || ADMIN_WHITELIST.includes(phone);

        // commands
        if (text.startsWith('/')) {
          const [cmd, ...args] = text.trim().split(' ');
          if (!isAdmin) {
            await sock.sendMessage(from, { text: `${replyPrefix()} Unauthorized.` });
            appendLog({ user: phone, action: 'unauthorized_command', command: cmd, args });
            continue;
          }

          if (cmd === '/start' || cmd === '/help') {
            await sock.sendMessage(from, { text: `${replyPrefix()} Ready. Mode=${MODE}. Persona=${persona.name}` });
            continue;
          }

          if (cmd === '/status') {
            const status = {
              mode: MODE,
              runCount: db.data.runCount,
              persona: persona.name
            };
            await sock.sendMessage(from, { text: `${replyPrefix()} Status: ${JSON.stringify(status)}` });
            appendLog({ user: phone, action: 'status_check' });
            continue;
          }

          if (cmd === '/run') {
            const raw = args.join(' ');
            if (!raw) {
              await sock.sendMessage(from, { text: `${replyPrefix()} Usage: /run <action_name or shell command>` });
              continue;
            }
            // safeguard: if persona requires confirm on "dangerous" words
            const lower = raw.toLowerCase();
            const dangerous = ['delete', 'rm ', 'shutdown', 'kill', 'format'];
            const containsDanger = dangerous.some(w => lower.includes(w));
            if (persona.style?.confirm_before_danger && containsDanger) {
              // save pending
              await sock.sendMessage(from, { text: `${replyPrefix()} Dangerous command detected. Confirm using /confirm_run` });
              // store pending per phone in db
              db.data.pending ||= {};
              db.data.pending[phone] = raw;
              await db.write();
              appendLog({ user: phone, action: 'pending_danger', command: raw });
              continue;
            }
            // execute
            const res = await executeAction(raw, sock, from);
            await sock.sendMessage(from, { text: `${replyPrefix()} Result: ${JSON.stringify(res)}` });
            continue;
          }

          if (cmd === '/confirm_run') {
            db.data.pending ||= {};
            const pending = db.data.pending?.[phone];
            if (!pending) {
              await sock.sendMessage(from, { text: `${replyPrefix()} No pending command.` });
              continue;
            }
            const res = await executeAction(pending, sock, from);
            delete db.data.pending[phone];
            await db.write();
            await sock.sendMessage(from, { text: `${replyPrefix()} Confirmed. Result: ${JSON.stringify(res)}` });
            continue;
          }

          await sock.sendMessage(from, { text: `${replyPrefix()} Unknown command. Use /help` });
          continue;
        }

        // non-command messages: you can add auto-responses or persona-based replies
        // e.g., if person asks "status" in plain text:
        if (/status/i.test(text)) {
          await sock.sendMessage(from, { text: `${replyPrefix()} Current mode: ${MODE}. Ask /status for more` });
          appendLog({ user: phone, action: 'status_word' });
        }
      }
    } catch (e) {
      logger.error(e);
    }
  });

  // schedule persona tasks
  if (persona.tasks) {
    for (const [taskName, def] of Object.entries(persona.tasks)) {
      const cronExpr = def.time; // expects 6-field cron (sec min hour day month dayOfWeek)
      try {
        cron.schedule(cronExpr, async () => {
          logger.info(`Running scheduled task ${taskName}`);
          // simple example: send morning report to admin(s)
          const message = (def.template || 'Task: ' + taskName).replace('{status_summary}', 'All systems OK');
          for (const admin of ADMIN_WHITELIST) {
            const jid = admin.replace('+', '') + '@s.whatsapp.net';
            await sock.sendMessage(jid, { text: `${replyPrefix()} [Scheduled:${taskName}] ${message}` });
          }
          appendLog({ user: 'system', action: 'scheduled_task', taskName });
        });
      } catch (err) {
        logger.error({ err }, `invalid cron for ${taskName}`);
      }
    }
  }

  return sock;
}

// central executor for actions
async function executeAction(rawCommand, sock, to) {
  db.data.runCount = (db.data.runCount || 0) + 1;
  await db.write();

  appendLog({ user: to.split('@')[0], action: 'execute', command: rawCommand });

  // In dryrun, just return
  if (MODE === 'dryrun') {
    return { status: 'dryrun', command: rawCommand };
  }

  // implement custom actions: predefined action names or shell commands
  // here: if command starts with "send:" -> send message to target
  if (rawCommand.startsWith('send:')) {
    const rest = rawCommand.slice(5).trim();
    const [targetPhone, ...msgParts] = rest.split(' ');
    const message = msgParts.join(' ');
    const jid = targetPhone.replace('+', '') + '@s.whatsapp.net';
    await sock.sendMessage(jid, { text: message });
    appendLog({ user: to.split('@')[0], action: 'send', target: targetPhone, message });
    return { status: 'sent', target: targetPhone };
  }

  // else, run as shell command (use with caution)
  const { exec } = require('child_process');
  return await new Promise((resolve) => {
    exec(rawCommand, { timeout: 60_000 }, (err, stdout, stderr) => {
      if (err) {
        appendLog({ user: to.split('@')[0], action: 'shell_err', err: err.message });
        resolve({ status: 'error', err: err.message, stderr });
      } else {
        appendLog({ user: to.split('@')[0], action: 'shell_ok', stdout });
        resolve({ status: 'ok', stdout });
      }
    });
  });
}

// start
startSock().catch(e => logger.error(e));  


FROM node:18-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --only=production
COPY . .
CMD ["node", "main.js"]   

import makeWASocket, { useMultiFileAuthState, DisconnectReason } from "@whiskeysockets/baileys";
import { Low } from "lowdb";
import { JSONFile } from "lowdb/node";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";
import cron from "node-cron";

dotenv.config();

// DB
const adapter = new JSONFile("db.json");
const db = new Low(adapter, { logs: [], feedback: {}, runCount: 0 });
await db.read();
db.data ||= { logs: [], feedback: {}, runCount: 0 };

// Persona
const persona = JSON.parse(fs.readFileSync("persona.json", "utf-8"));

// Admins
const ADMINS = persona.admins || [];
const isAdmin = (phone) => ADMINS.includes(phone);

// Helper
function appendLog(entry) {
  db.data.logs.push({ ts: new Date().toISOString(), ...entry });
  db.data.runCount++;
  db.write();
}
const replyPrefix = () => persona.style.reply_prefix || "";

// Bot Init
const { state, saveCreds } = await useMultiFileAuthState("auth_info");
const sock = makeWASocket({ auth: state });
sock.ev.on("creds.update", saveCreds);

sock.ev.on("messages.upsert", async ({ messages }) => {
  const m = messages[0];
  if (!m.message || !m.key.remoteJid) return;

  const from = m.key.remoteJid;
  const text = m.message.conversation || m.message.extendedTextMessage?.text || "";
  const phone = from.split("@")[0];
  const [cmd, ...args] = text.trim().split(/\s+/);

  if (!cmd.startsWith("/")) return;

  // --- Commands ---
  if (!isAdmin(phone)) {
    await sock.sendMessage(from, { text: `${replyPrefix()} Unauthorized.` });
    return;
  }

  if (cmd === "/logs") {
    const n = parseInt(args[0] || "20", 10);
    const logs = db.data.logs.slice(-n);
    const out = logs.map((x, i) => `${i}: ${x.ts} | ${x.user} | ${x.action} | ${x.command || ""} | ${x.result?.status || ""}`).join("\n\n");
    await sock.sendMessage(from, { text: out || "No logs." });
    appendLog({ user: phone, action: "view_logs" });
  }

  if (cmd === "/tasks") {
    const tasks = persona.tasks || {};
    const lines = Object.entries(tasks).map(([k,v]) => `${k} @ ${v.time} — ${v.description || ""}`);
    await sock.sendMessage(from, { text: `${replyPrefix()} Tasks:\n${lines.join("\n")}` });
    appendLog({ user: phone, action: "view_tasks" });
  }

  if (cmd === "/export_logs") {
    const fname = `logs_${Date.now()}.json`;
    fs.writeFileSync(fname, JSON.stringify(db.data.logs, null, 2));
    await sock.sendMessage(from, { document: { url: fname }, mimetype: "application/json", fileName: fname });
    appendLog({ user: phone, action: "export_logs" });
  }

  if (cmd === "/feedback") {
    const [id, decision] = args;
    if (!id || !decision) {
      await sock.sendMessage(from, { text: "Usage: /feedback <log_index> <accept|reject>" });
      return;
    }
    db.data.feedback[id] = decision;
    await db.write();
    await sock.sendMessage(from, { text: `${replyPrefix()} Feedback saved for log ${id}: ${decision}` });
    appendLog({ user: phone, action: "feedback", target: id, result: decision });
  }
});

// --- Scheduler ---
Object.entries(persona.tasks || {}).forEach(([name, task]) => {
  cron.schedule(task.time, () => {
    appendLog({ user: "system", action: "scheduled_task", taskName: name });
    console.log(`Task triggered: ${name}`);
  });
});
