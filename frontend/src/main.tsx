/* @refresh reload */
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/dm-sans/700.css";
import "@fontsource/dm-mono/400.css";
import "@fontsource/dm-mono/500.css";
import "./styles/index.css";

import { render } from "solid-js/web";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("index.html must contain #root");
}
render(() => <p class="p-8 font-sans">Venn Manager</p>, root);
