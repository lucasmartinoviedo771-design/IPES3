export const el = (tag, cls, txt) => {
  const x = document.createElement(tag);
  if (cls) x.className = cls;
  if (txt != null) x.textContent = txt;
  return x;
};

export function resetSelect(sel, placeholder) {
  sel.innerHTML = "";
  const opt = el("option", "", placeholder || "— Seleccioná —");
  opt.value = "";
  sel.appendChild(opt);
}