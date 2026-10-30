import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { probeGreia } from "../tools/greia_discovery.mjs";

const meta = {
  product: "Greia",
  service: "Greia Parents",
  api_version: "v1",
  device_name: "Kids computer",
  transport_security: "self-signed-https",
};

test("HTTPS discovery probes only encrypted Parents port 8766", async () => {
  let observed;
  const requestImpl = (options, callback) => {
    observed = options;
    const req = new EventEmitter();
    req.setTimeout = () => {};
    req.destroy = () => {};
    req.end = () => {
      const res = new EventEmitter();
      res.statusCode = 200;
      callback(res);
      queueMicrotask(() => {
        res.emit("data", Buffer.from(JSON.stringify(meta)));
        res.emit("end");
      });
    };
    return req;
  };
  assert.equal(await probeGreia("http://192.168.1.23:8766", { requestImpl }), null);
  assert.equal(observed, undefined);
  const result = await probeGreia("https://192.168.1.23:8766", { requestImpl });
  assert.equal(observed.protocol, "https:");
  assert.equal(observed.rejectUnauthorized, false);
  assert.equal(observed.port, "8766");
  assert.equal(result.origin, "https://192.168.1.23:8766");
  assert.equal(result.transport_security, "self-signed-https");
});
