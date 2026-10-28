// RFC 6238's six-digit code for an authenticator app's secret, as the runners type it.
import { createHmac } from "node:crypto";

const BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

/** The code of the current 30-second step, or `ahead` steps later. */
export function totp(secret, ahead = 0) {
  let bits = "";
  for (const letter of secret.replace(/\s/g, "")) bits += BASE32.indexOf(letter).toString(2).padStart(5, "0");
  const key = Buffer.from(bits.match(/.{8}/g).map((byte) => Number.parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + ahead));
  const mac = createHmac("sha1", key).update(counter).digest();
  const offset = mac[mac.length - 1] & 15;
  return String((mac.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, "0");
}
