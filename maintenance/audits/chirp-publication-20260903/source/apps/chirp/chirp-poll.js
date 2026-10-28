import { renderIcon, renderAvatar } from './chirp-shared.js';
import { L } from './chirp-utils.js';

export function renderPollCreator() {
  return `
<div class="compose-poll-creator" id="compose-poll-creator" style="display:none">
  <div class="poll-label">${L('pollOptions')}</div>
   <input type="text" class="poll-option-input" id="poll-opt-1" placeholder="${L('option1')}" />
   <input type="text" class="poll-option-input" id="poll-opt-2" placeholder="${L('option2')}" />
   <input type="text" class="poll-option-input" id="poll-opt-3" placeholder="${L('option3')}" />
   <input type="text" class="poll-option-input" id="poll-opt-4" placeholder="${L('option4')}" />
   <div class="poll-duration">
     <span>${L('pollClosesIn')}</span>
     <select id="poll-duration">
       <option value="1 hour">${L('1hour')}</option>
       <option value="1 day" selected>${L('1day')}</option>
       <option value="3 days">${L('3days')}</option>
       <option value="7 days">${L('7days')}</option>
    </select>
  </div>
</div>`;
}

export function buildPollFromContainer(container) {
  const pollCreator = container.querySelector('#compose-poll-creator');
  if (!pollCreator || pollCreator.style.display === 'none') return null;

  const opts = ['poll-opt-1', 'poll-opt-2', 'poll-opt-3', 'poll-opt-4']
    .map(id => container.querySelector(`#${id}`)?.value?.trim())
    .filter(Boolean);

  if (opts.length < 2) return null;

  const duration = container.querySelector('#poll-duration')?.value || '1 day';
  return {
    options: opts.map(label => ({ label, votes: 0 })),
    votes: {},
    closesIn: duration,
  };
}

export function attachPollToggleListener(container) {
  const pollBtn = container.querySelector('[data-tool="poll"]');
  const pollCreator = container.querySelector('#compose-poll-creator');

  pollBtn?.addEventListener('click', () => {
    if (!pollCreator) return;
    const hidden = pollCreator.style.display === 'none' || !pollCreator.style.display;
    pollCreator.style.display = hidden ? 'block' : 'none';
    pollBtn.classList.toggle('active', hidden);
  });
}
