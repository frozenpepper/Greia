import test from "node:test";
import assert from "node:assert/strict";
import { BrowserCredentialStore } from "../src/credential_store.js";
class MemoryStorage { constructor(){this.values=new Map();} getItem(key){return this.values.get(key)??null;} setItem(key,value){this.values.set(key,value);} removeItem(key){this.values.delete(key);} }
test("credentials are independently scoped by Greia origin",()=>{const store=new BrowserCredentialStore(new MemoryStorage());store.set("http://greia-one:8766","credential-one-12345");store.set("http://greia-two:8766","credential-two-12345");assert.equal(store.get("http://greia-one:8766"),"credential-one-12345");assert.equal(store.get("http://greia-two:8766"),"credential-two-12345");});
test("removing one credential does not affect another Greia",()=>{const store=new BrowserCredentialStore(new MemoryStorage());store.set("http://one","credential-one-12345");store.set("http://two","credential-two-12345");store.remove("http://one");assert.equal(store.get("http://one"),"");assert.equal(store.get("http://two"),"credential-two-12345");});
