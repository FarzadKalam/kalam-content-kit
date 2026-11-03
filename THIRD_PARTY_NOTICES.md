# Third-party material

- HyperFrames: https://github.com/heygen-com/hyperframes — Apache-2.0; bundled license at `vendor/hyperframes-LICENSE`. Vendored skill snapshot is pinned by per-file SHA-256 in `vendor/manifest.json`; its original installation did not record a source commit. Do not label it as the older Aitudio checkout commit.
- Remotion Agent Skills: https://github.com/remotion-dev/skills — officially distributed installation from `skills/remotion-best-practices`, version 4.0.539, exact file hashes in the same manifest. The upstream repository did not supply a root LICENSE or LICENSE.md when retrieved. No Apache/MIT license is inferred for it. Follow the upstream distribution and Remotion terms.
- Remotion runtime/CLI: dependencies only, no application source vendored. License eligibility: https://www.remotion.dev/docs/license/pricing . Installation does not purchase a company license.
- GSAP: installed dependency, terms shipped with the package apply: https://gsap.com/standard-license/ .
- FFmpeg/FFprobe: installed binary dependencies, their shipped license notices and build configurations apply. No proprietary encoder or media catalog is included.
- Vazirmatn: SIL Open Font License, included as `assets/fonts/Vazirmatn-OFL.txt`.
- Peyda: proprietary owner-provided font files. Originally supplied for the private team kit. The owner requested inclusion of the shared assets in this public content kit on 2026-11-03. The font remains proprietary; no open font license is inferred. Only genuine supplied weights are listed.
- Brand identity assets belong to their respective Kalam outlets and products. Owner authorized their use in this private editing kit. Per-asset sources in `assets/provenance.json`.
- SFX: originally synthesized local effects supplied from the owner's editing lab, not commercial music downloads. Shared for this team's projects; see provenance.
- The vendored media-use skill also ships its own bundled MP3 effects under `.agents/skills/media-use/audio/assets/sfx/`. These are part of the upstream skill snapshot, not recordings or customer media. They are the only MP3 exception in Git checks, and their upstream hashes are verified.

This repository's original-material notice does not override any of the above terms.

- KalamStudio: owner-authorized extraction from https://github.com/FarzadKalam/KalamStudio at the commit recorded in `vendor/studio/sources.json`. Offline prompt/validation rules and UI source snapshots are included; no backend service or credentials are included.
- TypeScript, Puppeteer Core, Sharp and adm-zip are installed pinned dependencies. Their respective package licenses apply.
