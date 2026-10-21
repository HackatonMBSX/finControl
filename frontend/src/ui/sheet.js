/* Bottom sheet (modal) de formulários. */
import { $ } from '../lib/format.js';

let sheetSubmitHandler = null;

export function openSheet(title, html, onSubmit){
  $('#sheetTitle').textContent = title;
  $('#sheetBody').innerHTML = html;
  sheetSubmitHandler = onSubmit || null;
  document.body.classList.add('sheet-open');
}

export function closeSheet(){
  document.body.classList.remove('sheet-open');
  sheetSubmitHandler = null;
}

export function initSheet(){
  $('#sheetClose').addEventListener('click', closeSheet);
  $('#sheetBg').addEventListener('click', closeSheet);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSheet(); });
  document.addEventListener('submit', e => {
    if (e.target.id === 'sheetForm' && sheetSubmitHandler){
      e.preventDefault();
      const data = Object.fromEntries(new FormData(e.target).entries());
      sheetSubmitHandler(data);
    }
  });
}
