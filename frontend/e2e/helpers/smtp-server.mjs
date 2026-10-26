// A minimal SMTP server for the browser runners (0.12 M1): plain, on 127.0.0.1, no login. It
// answers EHLO, MAIL, RCPT, DATA and QUIT; `refuse` makes it answer a recipient with a code, and
// every accepted message is kept in `messages` (headers and body as text).
import { createServer } from "node:net";

export async function startSmtp() {
  const messages = [];
  const refused = new Map();
  const sockets = new Set();
  const server = createServer((socket) => {
    sockets.add(socket);
    socket.on("close", () => sockets.delete(socket));
    socket.on("error", () => {});
    let pending = "";
    let data = null;
    const say = (text) => socket.write(`${text}\r\n`);
    say("220 fake.test ready");
    socket.on("data", (chunk) => {
      pending += chunk.toString("utf8");
      for (;;) {
        if (data !== null) {
          const end = pending.indexOf("\r\n.\r\n");
          if (end === -1) return;
          messages.push(pending.slice(0, end));
          pending = pending.slice(end + 5);
          data = null;
          say("250 queued");
          continue;
        }
        const newline = pending.indexOf("\r\n");
        if (newline === -1) return;
        const line = pending.slice(0, newline);
        pending = pending.slice(newline + 2);
        const verb = line.split(" ", 1)[0].toUpperCase();
        if (verb === "EHLO" || verb === "HELO") say("250 fake.test");
        else if (verb === "MAIL") say("250 ok");
        else if (verb === "RCPT") {
          const address = line.slice(line.indexOf("<") + 1, line.indexOf(">"));
          const answer = refused.get(address);
          say(answer ? `${answer.code} ${answer.text}` : "250 ok");
        } else if (verb === "DATA") {
          data = "";
          say("354 go ahead");
        } else if (verb === "QUIT") {
          say("221 bye");
          socket.end();
          return;
        } else say("250 ok");
      }
    });
  });
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  return {
    port: server.address().port,
    messages,
    refuse: (address, code, text) => refused.set(address, { code, text }),
    stop: () => {
      for (const socket of sockets) socket.destroy();
      server.close();
    },
  };
}
