/* @refresh reload */
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/dm-sans/700.css";
import "@fontsource/dm-mono/400.css";
import "@fontsource/dm-mono/500.css";
import "./styles/index.css";

import { render } from "solid-js/web";

import { createHttpApi } from "@/adapters/http";
import { App } from "@/ui/App";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("index.html must contain #root");
}
render(() => <App makeApi={(hooks) => createHttpApi(hooks)} />, root);
