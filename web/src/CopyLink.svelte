<script lang="ts">
  import { Icon } from "svelte-icons-pack";
  import { BsCheck2, BsLink45deg } from "svelte-icons-pack/bs";

  /** The link to copy, relative to this page. */
  let { href, title }: { href: string; title: string } = $props();

  let copied = $state(false);
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function copy() {
    const url = new URL(href, location.href).href;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Without the clipboard, show the link to copy by hand.
      prompt("Copy the link to this run:", url);
      return;
    }
    copied = true;
    clearTimeout(timer);
    timer = setTimeout(() => (copied = false), 2000);
  }
</script>

<button
  onclick={copy}
  {title}
  class="inline-flex items-center gap-1 text-xs text-muted transition-colors hover:text-fg"
>
  <Icon src={copied ? BsCheck2 : BsLink45deg} size={14} />
  <span aria-live="polite">{copied ? "Copied" : "Copy link"}</span>
</button>
