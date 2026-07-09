from __future__ import annotations
import json, shutil
from pathlib import Path

PACKS = {
    "spells": "Aurora Content - Spells",
    "classes": "Aurora Content - Classes",
    "subclasses": "Aurora Content - Subclasses",
    "species": "Aurora Content - Species and Races",
    "backgrounds": "Aurora Content - Backgrounds",
    "features": "Aurora Content - Features Feats Traits",
    "infusions": "Aurora Content - Artificer Infusions",
    "equipment": "Aurora Content - Equipment and Magic Items",
    "other": "Aurora Content - Other",
    "summons": "Aurora Content - Summons",
}

PACK_TYPES = {
    "summons": "Actor",
}

# v2.8: the compiler now ships a real Foundry-side runtime skeleton.  This is
# intentionally defensive: Foundry/D&D5e hook names changed across versions, so
# the runtime exposes a public API and listens to several likely activity hooks
# without crashing when a hook argument shape is different.
RUNTIME_JS = r'''
const MODULE_ID = "__MODULE_ID__";

function auroraLog(...args) {
  console.log(`Aurora Runtime |`, ...args);
}

function getModule() {
  return game.modules.get(MODULE_ID);
}

function getActivityFlag(activity) {
  return activity?.flags?.aurora?.runtime
    ?? activity?.toObject?.()?.flags?.aurora?.runtime
    ?? null;
}

function getItemFlag(item) {
  return item?.flags?.aurora?.runtime
    ?? item?.getFlag?.("aurora", "runtime")
    ?? null;
}

function firstActorFromContext(context) {
  return context?.actor
    ?? context?.item?.actor
    ?? context?.activity?.item?.actor
    ?? context?.workflow?.actor
    ?? canvas?.tokens?.controlled?.[0]?.actor
    ?? null;
}

function activityFromContext(context) {
  return context?.activity ?? context?.workflow?.activity ?? null;
}

function itemFromContext(context) {
  return context?.item ?? context?.activity?.item ?? context?.workflow?.item ?? null;
}

function formulaFromRuntime(runtime, fallback = "1") {
  return runtime?.formula || runtime?.roll || runtime?.healing?.formula || fallback;
}

function targetedTokens() {
  const targets = Array.from(game.user?.targets ?? []);
  if (targets.length) return targets;
  return canvas?.tokens?.controlled ?? [];
}

function actorName(actor) {
  return actor?.name ?? "Unknown Actor";
}

async function rollFormula(formula, actor, flavor) {
  const data = actor?.getRollData?.() ?? actor?.system ?? {};
  const roll = await new Roll(formula, data).evaluate();
  await roll.toMessage({
    speaker: ChatMessage.getSpeaker({ actor }),
    flavor,
  });
  return roll;
}

async function applyTempHpToActor(actor, value, sourceName = "Aurora Runtime") {
  if (!actor) return false;
  const current = Number(foundry.utils.getProperty(actor, "system.attributes.hp.temp") ?? 0);
  const next = Math.max(current, Number(value || 0));
  await actor.update({ "system.attributes.hp.temp": next });
  return true;
}

async function applyHealingToActor(actor, value, sourceName = "Aurora Runtime") {
  if (!actor) return false;
  const hp = actor.system?.attributes?.hp;
  if (!hp) return false;
  const current = Number(hp.value ?? 0);
  const max = Number(hp.max ?? current);
  const next = Math.min(max, current + Number(value || 0));
  await actor.update({ "system.attributes.hp.value": next });
  return true;
}

async function targetedTempHp(context = {}, runtime = {}) {
  const actor = firstActorFromContext(context);
  if (!actor) {
    ui.notifications?.warn("Aurora Runtime: nessun attore sorgente trovato.");
    return false;
  }
  const formula = formulaFromRuntime(runtime, "1");
  const roll = await rollFormula(formula, actor, runtime.label || "Aurora Temporary HP");
  const tokens = targetedTokens();
  if (!tokens.length) {
    ui.notifications?.warn("Aurora Runtime: seleziona/targetta almeno un token a cui applicare i temporary HP.");
    return false;
  }
  let applied = 0;
  for (const token of tokens) {
    if (await applyTempHpToActor(token.actor, roll.total, runtime.label)) applied++;
  }
  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `<p><strong>${runtime.label || "Temporary HP"}</strong>: applicati <strong>${roll.total}</strong> temporary HP a ${applied} bersagli.</p>`,
  });
  return true;
}

async function targetedHealing(context = {}, runtime = {}) {
  const actor = firstActorFromContext(context);
  if (!actor) {
    ui.notifications?.warn("Aurora Runtime: nessun attore sorgente trovato.");
    return false;
  }
  const formula = formulaFromRuntime(runtime, "1");
  const roll = await rollFormula(formula, actor, runtime.label || "Aurora Healing");
  const tokens = targetedTokens();
  if (!tokens.length) {
    ui.notifications?.warn("Aurora Runtime: seleziona/targetta almeno un token da curare.");
    return false;
  }
  let applied = 0;
  for (const token of tokens) {
    if (await applyHealingToActor(token.actor, roll.total, runtime.label)) applied++;
  }
  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `<p><strong>${runtime.label || "Healing"}</strong>: curati <strong>${roll.total}</strong> HP su ${applied} bersagli.</p>`,
  });
  return true;
}


function hpPath(actor, key) {
  return `system.attributes.hp.${key}`;
}

async function applyDamageToActor(actor, value, sourceName = "Aurora Runtime") {
  if (!actor) return false;
  const hp = actor.system?.attributes?.hp;
  if (!hp) return false;
  let damage = Math.max(0, Number(value || 0));
  const temp = Number(hp.temp ?? 0);
  const current = Number(hp.value ?? 0);
  const tempAfter = Math.max(0, temp - damage);
  damage = Math.max(0, damage - temp);
  const hpAfter = Math.max(0, current - damage);
  await actor.update({
    "system.attributes.hp.temp": tempAfter,
    "system.attributes.hp.value": hpAfter,
  });
  return true;
}

async function targetedDamage(context = {}, runtime = {}) {
  const actor = firstActorFromContext(context);
  if (!actor) {
    ui.notifications?.warn("Aurora Runtime: nessun attore sorgente trovato.");
    return false;
  }
  const formula = formulaFromRuntime(runtime, "1");
  const roll = await rollFormula(formula, actor, runtime.label || "Aurora Damage");
  const tokens = targetedTokens();
  if (!tokens.length) {
    ui.notifications?.warn("Aurora Runtime: targetta/seleziona almeno un token a cui applicare danno.");
    return false;
  }
  let applied = 0;
  for (const token of tokens) {
    if (await applyDamageToActor(token.actor, roll.total, runtime.label)) applied++;
  }
  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `<p><strong>${runtime.label || "Damage"}</strong>: applicati <strong>${roll.total}</strong> danni a ${applied} bersagli. ${runtime.damageType ? `Tipo: ${runtime.damageType}.` : ""}</p>`,
  });
  return true;
}

async function targetedSaveDamage(context = {}, runtime = {}) {
  // v2.8 non decide automaticamente chi supera o fallisce il TS: applica il danno
  // ai bersagli scelti e lascia il risultato del save alla chat/activity di dnd5e.
  // La gestione automatica save-half/save-none sarà un backend successivo.
  return targetedDamage(context, runtime);
}

async function runRuntimeAction(context = {}, explicitRuntime = null) {
  const activity = activityFromContext(context);
  const item = itemFromContext(context);
  const runtime = explicitRuntime || getActivityFlag(activity) || getItemFlag(item);
  if (!runtime?.action) return false;

  switch (runtime.action) {
    case "targeted-temphp":
      return targetedTempHp(context, runtime);
    case "targeted-healing":
      return targetedHealing(context, runtime);
    case "targeted-damage":
      return targetedDamage(context, runtime);
    case "targeted-save-damage":
      return targetedSaveDamage(context, runtime);
    default:
      auroraLog("Runtime action not implemented yet", runtime.action, runtime);
      return false;
  }
}

function normalizeHookArgs(...args) {
  const context = {};
  for (const arg of args) {
    if (!arg) continue;
    if (arg.constructor?.name?.toLowerCase?.().includes("activity")) context.activity = arg;
    if (arg.documentName === "Item" || arg.actor || arg.system?.activities) context.item = context.item ?? arg;
    if (arg.documentName === "Actor") context.actor = context.actor ?? arg;
    if (arg.activity || arg.item || arg.actor) Object.assign(context, arg);
  }
  return context;
}

Hooks.once("init", () => {
  const mod = getModule();
  if (mod) {
    mod.api = {
      run: runRuntimeAction,
      targetedTempHp,
      targetedHealing,
      targetedDamage,
      targetedSaveDamage,
      version: "2.8.0-alpha",
    };
  }
});

Hooks.once("ready", () => {
  auroraLog(`ready for ${MODULE_ID}. API: game.modules.get("${MODULE_ID}").api.run(...)`);
});

// Defensive hook bridge. These hooks may not all exist on every dnd5e version;
// registering them is safe and lets the runtime catch activity usage when the
// system exposes one of these events.
for (const hookName of [
  "dnd5e.preUseActivity",
  "dnd5e.useActivity",
  "dnd5e.postUseActivity",
  "dnd5e.preUseItem",
  "dnd5e.useItem",
  "dnd5e.postUseItem",
]) {
  Hooks.on(hookName, async (...args) => {
    try {
      const context = normalizeHookArgs(...args);
      await runRuntimeAction(context);
    } catch (err) {
      console.error(`Aurora Runtime | ${hookName} failed`, err);
    }
  });
}
'''


def write_module(out_dir: str | Path, pack_docs: dict[str, list[dict]], module_id="aurora-content-pack", title="Aurora Content Pack", version="0.5.0-alpha") -> Path:
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    (out / "packs").mkdir(parents=True)
    (out / "scripts").mkdir(parents=True)
    for pack, docs in pack_docs.items():
        with open(out / "packs" / f"{pack}.db", "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    (out / "scripts" / "runtime.js").write_text(RUNTIME_JS.replace("__MODULE_ID__", module_id), encoding="utf-8")
    module = {
        "id": module_id,
        "name": module_id,
        "title": title,
        "description": "D&D5e content compiled from Aurora XML. Extends the official D&D5e system and includes the Aurora Runtime automation layer.",
        "version": version,
        "authors": [{"name": "Daniel / Aurora Compiler"}],
        "compatibility": {"minimum": "12", "verified": "14"},
        "relationships": {"systems": [{"id": "dnd5e", "type": "system", "compatibility": {}}]},
        "esmodules": ["scripts/runtime.js"],
        "packs": [
            {"name": name, "label": label, "path": f"packs/{name}.db", "type": PACK_TYPES.get(name, "Item"), "system": "dnd5e", "ownership": {"PLAYER": "OBSERVER", "ASSISTANT": "OWNER"}}
            for name, label in PACKS.items() if name in pack_docs
        ]
    }
    (out / "module.json").write_text(json.dumps(module, indent=2), encoding="utf-8")
    return out
