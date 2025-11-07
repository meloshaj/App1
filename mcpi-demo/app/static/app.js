(() => {
    const $ = (sel) => document.querySelector(sel);

    // remove health UI
    const form = $('#piForm');
    const samplesInput = $('#samples');
    const tasksInput = $('#tasks');
    const digitsInput = $('#digits');
    const batchStatus = $('#batchStatus');
    const resultsBody = document.querySelector('#resultsBody');
    const mEstimate = $('#m_estimate');
    const mActual = $('#m_actual');
    const mDiff = $('#m_diff');
    const mIters = $('#m_iters');
    const mElapsed = $('#m_elapsed');
    const mCompleted = $('#m_completed');
    const yearEl = $('#year');

    if (yearEl) {
        yearEl.textContent = String(new Date().getFullYear());
    }


    function toFixedSafe(val, digits) {
        try { return Number(val).toFixed(digits); } catch { return String(val); }
    }

    function renderActual(digits) {
        const actual = Number(Math.PI.toFixed(Math.min(15, Math.max(1, digits))));
        mActual.textContent = actual.toFixed(digits);
        return actual;
    }

    async function startBatch(samples, tasks, digits) {
        batchStatus.textContent = 'Submitting batch...';
        if (resultsBody) resultsBody.innerHTML = '';
        mEstimate.textContent = '—';
        mDiff.textContent = '—';
        mIters.textContent = samples.toLocaleString();  // Total samples (split across tasks)
        mElapsed.textContent = '0.0s';
        mCompleted.textContent = '0/' + tasks;
        const actualPi = renderActual(digits);

        const startedAt = Date.now();
        const res = await fetch('/api/pi/batch/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ samples, tasks })
        });
        const json = await res.json();
        if (!json.task_ids || !Array.isArray(json.task_ids)) {
            batchStatus.textContent = 'Failed to start batch';
            return;
        }
        const ids = json.task_ids;
        batchStatus.textContent = 'Started ' + ids.length + ' tasks';

        // Poll all tasks and aggregate results as they complete
        const results = [];
        let completed = 0;
        const interval = 500;
        const timers = ids.map((id, idx) => setInterval(async () => {
            try {
                const r = await fetch(`/api/pi/status/${id}`);
                const s = await r.json();
                if (s.ready && s.result) {
                    clearInterval(timers[idx]);
                    results.push(s.result);
                    completed += 1;
                    mCompleted.textContent = completed + '/' + ids.length;

                    // Aggregate by combining raw counts across all completed tasks
                    // This is statistically better than averaging individual estimates
                    const totalInside = results.reduce((acc, it) => acc + Number(it.inside || 0), 0);
                    const totalSamples = results.reduce((acc, it) => acc + Number(it.samples || 0), 0);
                    
                    // Update iterations to show actual total samples processed
                    mIters.textContent = totalSamples.toLocaleString();
                    
                    if (totalSamples > 0) {
                        // Combined π estimate from aggregated raw counts
                        const combinedPi = 4.0 * (totalInside / totalSamples);
                        const diff = Math.abs(combinedPi - actualPi);
                        mEstimate.textContent = toFixedSafe(combinedPi, digits);
                        mDiff.textContent = toFixedSafe(diff, digits);
                    }
                    
                    // append row
                    if (resultsBody) {
                        const idx = results.length;
                        const tr = document.createElement('tr');
                        const piVal = Number(s.result.pi || 0);
                        const taskSamples = Number(s.result.samples || 0);
                        const err = Number(s.result.error_abs || Math.abs(piVal - Math.PI));
                        tr.innerHTML = `
                            <td>${idx}</td>
                            <td>${id}</td>
                            <td>${toFixedSafe(piVal, digits)}</td>
                            <td>${taskSamples.toLocaleString()}</td>
                            <td>${toFixedSafe(err, digits)}</td>
                        `;
                        resultsBody.appendChild(tr);
                    }

                    if (completed === ids.length) {
                        const elapsed = (Date.now() - startedAt) / 1000;
                        mElapsed.textContent = toFixedSafe(elapsed, 2) + 's';
                        batchStatus.textContent = 'Batch complete';
                    }
                }
            } catch (e) {
                // ignore transient errors while polling
            }
        }, interval));
    }

    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const samples = Math.max(1, parseInt(samplesInput.value, 10) || 1000000);
            const tasks = Math.max(1, parseInt(tasksInput.value, 10) || 4);
            const digits = Math.max(1, Math.min(15, parseInt(digitsInput.value, 10) || 6));
            startBatch(samples, tasks, digits);
        });
    }
})();


