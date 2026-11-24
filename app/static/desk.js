const sample = document.querySelector('#sample');
sample.addEventListener('change', () => {
  document.querySelector('input[name=run]')?.remove();
  document.querySelector('input[name=trial]')?.remove();
});
document.querySelector('#print-book').addEventListener('click', () => window.print());
const rerun = document.querySelector('#rerun');
rerun?.addEventListener('click', async () => {
  const feedback = document.querySelector('#feedback');
  rerun.disabled = true;
  feedback.textContent = '复算中…';
  try {
    const res = await fetch(`/api/journal/${rerun.dataset.run}/rerun`, {method:'POST'});
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || '复算失败');
    feedback.textContent = data.reused ? '复算一致，沿用原簿' : '新簿已归档';
  } catch (error) {
    feedback.textContent = `${error.message}，请重试。`;
  } finally { rerun.disabled = false; }
});
const archive = document.querySelector('#archive-trial');
archive?.addEventListener('click', async () => {
  const feedback = document.querySelector('#trial-feedback');
  archive.disabled = true;
  feedback.textContent = '试算留档中…';
  try {
    const res = await fetch('/api/dredging/trials', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({sample: archive.dataset.sample})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || '试算失败');
    feedback.textContent = data.reused ? `同源试算已留档，沿用 ${data.trial_id.slice(0, 12)}` : `试算号 ${data.trial_id.slice(0, 12)} 已留档`;
    const url = new URL(window.location.href);
    url.searchParams.set('trial', data.trial_id);
    window.history.replaceState(null, '', url);
  } catch (error) {
    feedback.textContent = `${error.message}，原簿未改动。`;
  } finally { archive.disabled = false; }
});
