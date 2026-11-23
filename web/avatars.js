/**
 * Procedural crisp SVG character portraits for Griductive.
 * Hand-tuned profiles for the roster + deterministic fallback for any custom puzzle name.
 */
(function () {
  const SKINS = [
    { base: "#F7D3B0", shadow: "#E2B289", blush: "#E79586" }, // fair warm
    { base: "#E9B78D", shadow: "#CE9569", blush: "#DC8576" }, // light golden
    { base: "#CE8F62", shadow: "#B17247", blush: "#C5715D" }, // warm tan
    { base: "#A36943", shadow: "#84502E", blush: "#9F5A46" }, // caramel brown
    { base: "#73462D", shadow: "#58331E", blush: "#7D4533" }, // deep espresso
  ];

  const HAIRS = {
    espresso: { main: "#261E1A", hi: "#3E322C" },
    chestnut: { main: "#5A3825", hi: "#784E36" },
    auburn:   { main: "#A24F2A", hi: "#C46B3E" },
    blonde:   { main: "#E0AE56", hi: "#F2C978" },
    honey:    { main: "#C68B49", hi: "#DEA664" },
    raven:    { main: "#1D1C24", hi: "#353342" },
    silver:   { main: "#8F8B8A", hi: "#B3AEAC" },
  };

  // Curated diverse traits for the 25 roster names (looks like handcrafted cast art)
  const PROFILES = {
    Abel:   { skin: 0, hair: "blonde",   style: "quiff",    glasses: false },
    Bea:    { skin: 4, hair: "raven",    style: "bun",      glasses: false },
    Clara:  { skin: 0, hair: "blonde",   style: "highbun",  glasses: false },
    Derek:  { skin: 1, hair: "chestnut", style: "parted",   glasses: false },
    Eliza:  { skin: 2, hair: "espresso", style: "bob",      glasses: false },
    Franz:  { skin: 3, hair: "espresso", style: "short",    glasses: false, stubble: true },
    Grant:  { skin: 0, hair: "espresso", style: "parted",   glasses: true  },
    Hannah: { skin: 0, hair: "espresso", style: "long",     glasses: false },
    Ivy:    { skin: 2, hair: "auburn",   style: "wavy",     glasses: true  },
    Jonas:  { skin: 3, hair: "chestnut", style: "curly",    glasses: false },
    Karl:   { skin: 2, hair: "chestnut", style: "spiky",    glasses: false },
    Leo:    { skin: 1, hair: "auburn",   style: "curly",    glasses: false },
    Mara:   { skin: 0, hair: "blonde",   style: "bob",      glasses: false },
    Noah:   { skin: 2, hair: "raven",    style: "short",    glasses: true  },
    Owen:   { skin: 4, hair: "raven",    style: "fade",     glasses: false },
    Priya:  { skin: 3, hair: "raven",    style: "long",     glasses: false },
    Quilla: { skin: 1, hair: "auburn",   style: "ponytail", glasses: false },
    Roy:    { skin: 1, hair: "honey",    style: "parted",   glasses: false },
    Sophia: { skin: 3, hair: "espresso", style: "wavy",     glasses: false },
    Tom:    { skin: 1, hair: "auburn",   style: "quiff",    glasses: false },
    Uma:    { skin: 3, hair: "raven",    style: "highbun",  glasses: true  },
    Victor: { skin: 0, hair: "silver",   style: "parted",   glasses: false },
    Wendy:  { skin: 4, hair: "espresso", style: "curlybob", glasses: false },
    Xavier: { skin: 2, hair: "raven",    style: "quiff",    glasses: false },
    Yara:   { skin: 1, hair: "chestnut", style: "long",     glasses: false },
  };

  const OUTFITS = {
    Astronaut: { coat: "#E4E8E6", accent: "#E07A47", collar: "#4A6670" },
    Cook:      { coat: "#F4EFE7", accent: "#CC5446", collar: "#D7CFC2" },
    Chef:      { coat: "#F4EFE7", accent: "#CC5446", collar: "#D7CFC2" },
    Guard:     { coat: "#344C66", accent: "#E2B14D", collar: "#1E2E40" },
    Detective: { coat: "#8D7357", accent: "#4C3B2B", collar: "#6B553E" },
    Clerk:     { coat: "#476C65", accent: "#E5DAC8", collar: "#2F4A45" },
    Farmer:    { coat: "#C27C3E", accent: "#426282", collar: "#8F5424" },
    Painter:   { coat: "#7F587D", accent: "#E7C568", collar: "#593A57" },
    Pilot:     { coat: "#3A5270", accent: "#E5BD5F", collar: "#243449" },
    Doctor:    { coat: "#EDF2F0", accent: "#3B8C7A", collar: "#C9D8D3" },
  };

  function hashName(name) {
    let h = 0;
    for (let i = 0; i < name.length; i++) {
      h = (h * 31 + name.charCodeAt(i)) >>> 0;
    }
    return h;
  }

  function getProfile(name) {
    if (PROFILES[name]) return PROFILES[name];
    const h = hashName(name);
    const hairKeys = Object.keys(HAIRS);
    const styles = ["quiff", "parted", "short", "curly", "bob", "long", "highbun", "wavy"];
    return {
      skin: h % SKINS.length,
      hair: hairKeys[(h >> 3) % hairKeys.length],
      style: styles[(h >> 6) % styles.length],
      glasses: (h % 5) === 0,
    };
  }

  function backHairSVG(style, h) {
    switch (style) {
      case "long":
        return `
          <path d="M18 32 C16 44, 15 62, 20 71 L60 71 C65 62, 64 44, 62 32 C61 17, 52 10, 40 10 C28 10, 19 17, 18 32 Z" fill="${h.main}"/>
          <path d="M22 33 C20 45, 20 58, 24 67" stroke="${h.hi}" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.45"/>`;
      case "bob":
        return `
          <path d="M17 34 C15 47, 17 58, 24 61 L56 61 C63 58, 65 47, 63 34 C62 18, 52 10, 40 10 C28 10, 18 18, 17 34 Z" fill="${h.main}"/>`;
      case "wavy":
        return `
          <path d="M16 34 C12 45, 16 56, 20 65 C28 68, 52 68, 60 65 C64 56, 68 45, 64 34 C62 18, 52 10, 40 10 C28 10, 18 18, 16 34 Z" fill="${h.main}"/>
          <circle cx="19" cy="52" r="6" fill="${h.main}"/>
          <circle cx="61" cy="52" r="6" fill="${h.main}"/>`;
      case "curlybob":
        return `
          <circle cx="20" cy="36" r="9" fill="${h.main}"/>
          <circle cx="60" cy="36" r="9" fill="${h.main}"/>
          <circle cx="19" cy="49" r="8" fill="${h.main}"/>
          <circle cx="61" cy="49" r="8" fill="${h.main}"/>
          <circle cx="28" cy="18" r="10" fill="${h.main}"/>
          <circle cx="52" cy="18" r="10" fill="${h.main}"/>
          <circle cx="40" cy="15" r="11" fill="${h.main}"/>`;
      case "highbun":
        return `
          <circle cx="40" cy="10" r="9.5" fill="${h.main}"/>
          <path d="M35 8 C38 5, 43 5, 45 8" stroke="${h.hi}" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.6"/>
          <ellipse cx="40" cy="29" rx="22" ry="18" fill="${h.main}"/>`;
      case "bun":
        return `
          <circle cx="40" cy="12" r="8.5" fill="${h.main}"/>
          <ellipse cx="40" cy="30" rx="21" ry="17" fill="${h.main}"/>`;
      case "ponytail":
        return `
          <path d="M56 30 C67 34, 70 49, 64 62 C59 60, 56 51, 54 41 Z" fill="${h.main}"/>
          <ellipse cx="40" cy="30" rx="21" ry="17" fill="${h.main}"/>`;
      case "curly":
        return `
          <circle cx="24" cy="24" r="8" fill="${h.main}"/>
          <circle cx="56" cy="24" r="8" fill="${h.main}"/>
          <circle cx="33" cy="16" r="8.5" fill="${h.main}"/>
          <circle cx="47" cy="16" r="8.5" fill="${h.main}"/>
          <circle cx="40" cy="14" r="8" fill="${h.main}"/>`;
      default:
        return "";
    }
  }

  function frontHairSVG(style, h) {
    switch (style) {
      case "quiff":
        return `
          <path d="M21 34 C20 20, 28 11, 41 11 C53 11, 60 19, 59 34 C56 26, 51 22, 43 22 C35 22, 27 25, 21 34 Z" fill="${h.main}"/>
          <path d="M31 15 C38 11, 48 13, 52 18" stroke="${h.hi}" stroke-width="2.2" fill="none" stroke-linecap="round" opacity="0.55"/>`;
      case "parted":
        return `
          <path d="M21 35 C20 19, 29 12, 41 12 C52 12, 60 19, 59 35 C55 26, 48 23, 36 24 C29 25, 24 28, 21 35 Z" fill="${h.main}"/>
          <path d="M29 17 C36 14, 45 15, 51 19" stroke="${h.hi}" stroke-width="1.8" fill="none" stroke-linecap="round" opacity="0.5"/>`;
      case "spiky":
        return `
          <path d="M21 34 L21 22 L27 14 L32 19 L39 10 L45 18 L52 13 L58 21 L59 34 C54 25, 47 23, 40 23 C33 23, 26 25, 21 34 Z" fill="${h.main}"/>`;
      case "short":
        return `
          <path d="M21 34 C21 20, 29 13, 40 13 C51 13, 59 20, 59 34 C54 26, 48 23, 40 23 C32 23, 26 26, 21 34 Z" fill="${h.main}"/>`;
      case "fade":
        return `
          <path d="M22 31 C22 19, 29 13, 40 13 C51 13, 58 19, 58 31 C53 24, 47 21, 40 21 C33 21, 27 24, 22 31 Z" fill="${h.main}"/>`;
      case "curly":
      case "curlybob":
        return `
          <circle cx="26" cy="23" r="6.5" fill="${h.main}"/>
          <circle cx="35" cy="19" r="7" fill="${h.main}"/>
          <circle cx="45" cy="19" r="7" fill="${h.main}"/>
          <circle cx="54" cy="23" r="6.5" fill="${h.main}"/>`;
      case "bob":
      case "long":
      case "wavy":
        return `
          <path d="M20 36 C20 20, 29 12, 40 12 C51 12, 60 20, 60 36 C55 27, 48 23, 42 22 C37 26, 29 27, 20 36 Z" fill="${h.main}"/>
          <path d="M28 17 C35 14, 44 14, 50 18" stroke="${h.hi}" stroke-width="1.8" fill="none" stroke-linecap="round" opacity="0.5"/>`;
      case "highbun":
      case "bun":
      case "ponytail":
        return `
          <path d="M20 35 C20 19, 29 13, 40 13 C51 13, 60 19, 60 35 C54 25, 47 22, 40 22 C33 22, 26 25, 20 35 Z" fill="${h.main}"/>`;
      default:
        return "";
    }
  }

  function outfitDetailsSVG(profession, outfit, compact) {
    switch (profession) {
      case "Astronaut":
        return `
          <path d="M22 66 Q40 60 58 66" stroke="${outfit.accent}" stroke-width="3.2" fill="none"/>
          <path d="M32 58 Q40 64 48 58" stroke="${outfit.collar}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`;
      case "Cook":
      case "Chef":
        return `
          <path d="M32 58 L40 66 L48 58 Z" fill="${outfit.accent}"/>
          ${compact ? "" : '<circle cx="36" cy="70" r="1.4" fill="#9E9589"/><circle cx="44" cy="70" r="1.4" fill="#9E9589"/>'}`;
      case "Farmer":
        return `
          <rect x="27" y="59" width="5" height="19" rx="1.5" fill="${outfit.accent}"/>
          <rect x="48" y="59" width="5" height="19" rx="1.5" fill="${outfit.accent}"/>
          ${compact ? "" : '<circle cx="29.5" cy="67" r="1.4" fill="#E6C373"/><circle cx="50.5" cy="67" r="1.4" fill="#E6C373"/>'}`;
      case "Doctor":
        return `
          <path d="M33 58 L40 73 L47 58 Z" fill="${outfit.accent}"/>
          ${compact ? "" : `
          <path d="M30 59 C27 66, 29 72, 34 73" stroke="#2D4A45" stroke-width="2.1" fill="none" stroke-linecap="round"/>
          <path d="M50 59 C53 66, 51 72, 46 73" stroke="#2D4A45" stroke-width="2.1" fill="none" stroke-linecap="round"/>
          <circle cx="34" cy="73" r="2.6" fill="#B5C6C2" stroke="#2D4A45" stroke-width="1"/>`}`;
      case "Clerk":
        return `
          <path d="M32 58 L40 68 L48 58 Z" fill="${outfit.accent}"/>
          <polygon points="35,62 40,64.5 35,67" fill="#C45348"/>
          <polygon points="45,62 40,64.5 45,67" fill="#C45348"/>
          <circle cx="40" cy="64.5" r="1.6" fill="#9B3930"/>`;
      case "Detective":
        return `
          <path d="M29 58 L37 72 L40 66 L43 72 L51 58" fill="${outfit.collar}" opacity="0.85"/>
          <path d="M37 59 L40 71 L43 59 Z" fill="${outfit.accent}"/>`;
      case "Guard":
      case "Pilot":
        return `
          <path d="M33 58 L40 69 L47 58 Z" fill="#EFEAE2"/>
          <path d="M38.5 60 L40 70 L41.5 60 Z" fill="${outfit.collar}"/>
          ${compact ? "" : `<rect x="47" y="65" width="7" height="4" rx="1.5" fill="${outfit.accent}"/>`}`;
      case "Painter":
        return `
          <path d="M25 66 Q40 63 55 66" stroke="${outfit.accent}" stroke-width="2.5" fill="none" opacity="0.85"/>
          <path d="M23 72 Q40 69 57 72" stroke="#D96C62" stroke-width="2.2" fill="none" opacity="0.8"/>`;
      default:
        return `<path d="M33 58 L40 66 L47 58 Z" fill="${outfit.accent}"/>`;
    }
  }

  function headwearSVG(profession, outfit, compact) {
    switch (profession) {
      case "Cook":
      case "Chef":
        return `
          <g>
            <circle cx="31" cy="11" r="6.5" fill="#F8F4EC"/>
            <circle cx="40" cy="9" r="7.5" fill="#F8F4EC"/>
            <circle cx="49" cy="11" r="6.5" fill="#F8F4EC"/>
            <rect x="26" y="13" width="28" height="7" rx="2" fill="#ECE6DA"/>
          </g>`;
      case "Detective":
        return `
          <g>
            <ellipse cx="40" cy="19" rx="23" ry="3.8" fill="${outfit.collar}"/>
            <path d="M25 19 L28 8 C33 6, 47 6, 52 8 L55 19 Z" fill="${outfit.coat}"/>
            <rect x="25.8" y="15.5" width="28.4" height="3.2" rx="1" fill="${outfit.accent}"/>
          </g>`;
      case "Painter":
        return `
          <g>
            <ellipse cx="38" cy="15" rx="17" ry="7.5" transform="rotate(-11 38 15)" fill="${outfit.coat}"/>
            <path d="M37 8 L39 4" stroke="${outfit.coat}" stroke-width="2.4" stroke-linecap="round"/>
          </g>`;
      case "Guard":
      case "Pilot":
        return `
          <g>
            <path d="M23 19 L26 9 C32 6, 48 6, 54 9 L57 19 Z" fill="${outfit.coat}"/>
            <path d="M21 19 Q40 23 59 19 Q40 16 21 19 Z" fill="${outfit.collar}"/>
            ${compact ? "" : `<circle cx="40" cy="13" r="2.6" fill="${outfit.accent}"/>`}
          </g>`;
      default:
        return "";
    }
  }

  window.renderAvatarSVG = function renderAvatarSVG(person, compact = false) {
    const profile = getProfile(person.name);
    const skin = SKINS[profile.skin];
    const hair = HAIRS[profile.hair] || HAIRS.espresso;
    const outfit = OUTFITS[person.profession] || { coat: "#677870", accent: "#D5C8B7", collar: "#495650" };
    const showGlasses = profile.glasses || person.profession === "Clerk";

    return `
      <svg class="avatar-svg ${compact ? "avatar-compact" : ""}" viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        ${backHairSVG(profile.style, hair)}
        <!-- Torso / Shoulders -->
        <path d="M13 78 C14 63, 24 57, 40 57 C56 57, 66 63, 67 78 Z" fill="${outfit.coat}"/>
        ${outfitDetailsSVG(person.profession, outfit, compact)}
        <!-- Neck -->
        <rect x="34" y="48" width="12" height="13" rx="5" fill="${skin.base}"/>
        <path d="M34 50 Q40 55 46 50 L46 54 Q40 58 34 54 Z" fill="${skin.shadow}" opacity="0.7"/>
        <!-- Ears -->
        <circle cx="20.5" cy="38" r="4.2" fill="${skin.base}"/>
        <circle cx="59.5" cy="38" r="4.2" fill="${skin.base}"/>
        <!-- Head -->
        <rect x="21" y="16" width="38" height="37" rx="18" fill="${skin.base}"/>
        <!-- Front Hair -->
        ${frontHairSVG(profile.style, hair)}
        <!-- Eyebrows -->
        ${compact ? "" : `
          <path d="M29 31.5 Q32.5 29.8 36 31.3" stroke="${hair.main}" stroke-width="1.8" fill="none" stroke-linecap="round"/>
          <path d="M44 31.3 Q47.5 29.8 51 31.5" stroke="${hair.main}" stroke-width="1.8" fill="none" stroke-linecap="round"/>
        `}
        <!-- Eyes -->
        <circle cx="32.5" cy="36.5" r="2.5" fill="#231C19"/>
        <circle cx="47.5" cy="36.5" r="2.5" fill="#231C19"/>
        ${compact ? "" : `
          <circle cx="31.7" cy="35.6" r="0.85" fill="#FFFBF5"/>
          <circle cx="46.7" cy="35.6" r="0.85" fill="#FFFBF5"/>
          <!-- Soft blush -->
          <ellipse cx="27.5" cy="41.5" rx="3.1" ry="1.7" fill="${skin.blush}" opacity="0.48"/>
          <ellipse cx="52.5" cy="41.5" rx="3.1" ry="1.7" fill="${skin.blush}" opacity="0.48"/>
        `}
        <!-- Subtle smile -->
        <path d="M36 44.5 Q40 47.6 44 44.5" stroke="${skin.shadow}" stroke-width="${compact ? 2.2 : 1.9}" fill="none" stroke-linecap="round"/>
        <!-- Glasses -->
        ${showGlasses ? `
          <g stroke="#3A312C" stroke-width="${compact ? 1.8 : 1.5}" fill="rgba(255,255,255,0.08)">
            <circle cx="32.5" cy="36.5" r="5.3"/>
            <circle cx="47.5" cy="36.5" r="5.3"/>
            <line x1="37.8" y1="36.5" x2="42.2" y2="36.5"/>
          </g>` : ""}
        <!-- Profession Headwear -->
        ${headwearSVG(person.profession, outfit, compact)}
      </svg>`;
  };
})();

