/**
 * Executive Dashboard - Vanilla JavaScript Frontend Controller
 */

let currentPage = 1;
let currentFilter = 'ALL';
let currentSearch = '';
let searchTimeout = null;
let batchPollInterval = null;
let activeDrawerProduct = null;
let categorySearchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchMetrics();
    fetchProducts(1);
    checkInitialBatchStatus();

    // Setup search input listener
    const searchInput = document.getElementById('product-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const val = e.target.value.trim();
            document.getElementById('search-clear-btn').classList.toggle('hidden', !val);
            searchTimeout = setTimeout(() => {
                currentSearch = val;
                fetchProducts(1);
            }, 300);
        });
    }
});

// Toast notification helper
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'info';
    let iconColor = 'text-blue-400';
    if (type === 'success') {
        icon = 'check-circle';
        iconColor = 'text-emerald-400';
    } else if (type === 'warning') {
        icon = 'alert-triangle';
        iconColor = 'text-amber-400';
    } else if (type === 'error') {
        icon = 'x-circle';
        iconColor = 'text-rose-400';
    }

    toast.innerHTML = `
        <i data-lucide="${icon}" class="w-4 h-4 ${iconColor}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Fetch Metrics Summary
async function fetchMetrics() {
    try {
        const resp = await fetch('/api/metrics/');
        if (!resp.ok) return;
        const data = await resp.json();

        document.getElementById('metric-total').innerText = Number(data.total_products).toLocaleString();
        document.getElementById('metric-processed').innerText = Number(data.processed_count).toLocaleString();
        document.getElementById('metric-pending').innerText = Number(data.pending_count).toLocaleString();
        document.getElementById('metric-review').innerText = Number(data.requires_review_count).toLocaleString();
        document.getElementById('metric-confidence').innerText = `${data.average_confidence}%`;

        const pct = data.total_products > 0 ? ((data.processed_count / data.total_products) * 100).toFixed(1) : 0;
        document.getElementById('metric-processed-pct').innerText = `${pct}%`;

        // Update nav badge and filter tab badge
        const navBadge = document.getElementById('nav-review-badge');
        const tabReviewCount = document.getElementById('tab-review-count');
        if (data.requires_review_count > 0) {
            navBadge.innerText = data.requires_review_count;
            navBadge.classList.remove('hidden');
            tabReviewCount.innerText = data.requires_review_count;
        } else {
            navBadge.classList.add('hidden');
            tabReviewCount.innerText = '0';
        }

    } catch (e) {
        console.error('Failed to fetch metrics:', e);
    }
}

// Fetch Products Table
async function fetchProducts(page = 1) {
    currentPage = page;
    const tbody = document.getElementById('product-table-body');
    tbody.innerHTML = `
        <tr>
            <td colspan="8" class="text-center py-12 text-slate-500">
                <i data-lucide="loader-2" class="w-6 h-6 mx-auto animate-spin text-blue-500 mb-2"></i>
                Loading products from database...
            </td>
        </tr>
    `;
    lucide.createIcons();

    let url = `/api/products/?page=${page}`;
    if (currentSearch) {
        url += `&search=${encodeURIComponent(currentSearch)}`;
    }
    if (currentFilter && currentFilter !== 'ALL') {
        url += `&status=${currentFilter}`;
    }

    try {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error('API request failed');
        const data = await resp.json();

        renderProductTable(data);
        updatePaginationControls(data);
    } catch (e) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-8 text-rose-400">
                    <i data-lucide="alert-circle" class="w-6 h-6 mx-auto mb-2"></i>
                    Failed to load products: ${e.message}
                </td>
            </tr>
        `;
        lucide.createIcons();
    }
}

// Render Table Rows
function renderProductTable(data) {
    const tbody = document.getElementById('product-table-body');
    const items = data.results || [];

    if (items.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-12 text-slate-400">
                    <i data-lucide="inbox" class="w-8 h-8 mx-auto text-slate-600 mb-2"></i>
                    No products found matching the criteria.
                </td>
            </tr>
        `;
        lucide.createIcons();
        return;
    }

    let html = '';
    items.forEach(p => {
        const clf = p.classification || {};
        const status = clf.status || 'UNPROCESSED';
        const confidence = clf.confidence_score || 0;
        const predictedCategory = clf.predicted_category_name || '<span class="text-slate-500 italic">Not Classified Yet</span>';
        
        let statusBadge = '';
        if (status === 'CLASSIFIED') {
            statusBadge = '<span class="badge-status badge-classified">Classified</span>';
        } else if (status === 'REQUIRES_REVIEW') {
            statusBadge = '<span class="badge-status badge-review">Review Needed</span>';
        } else if (status === 'APPROVED' || status === 'MANUALLY_OVERRIDDEN') {
            statusBadge = '<span class="badge-status badge-approved">Approved</span>';
        } else {
            statusBadge = '<span class="badge-status badge-unprocessed">Unprocessed</span>';
        }

        let barColor = 'bg-blue-500';
        if (confidence >= 70) barColor = 'bg-emerald-400';
        else if (confidence >= 60) barColor = 'bg-blue-400';
        else if (confidence > 0) barColor = 'bg-amber-400';
        else barColor = 'bg-slate-700';

        const imgSrc = p.primary_image_url || '';
        const imgHtml = imgSrc 
            ? `<img src="${imgSrc}" alt="" class="w-9 h-9 rounded object-cover border border-slate-700 bg-slate-800" onerror="this.src=''; this.classList.add('hidden'); this.nextElementSibling.classList.remove('hidden');"><div class="w-9 h-9 rounded bg-slate-800 border border-slate-700 hidden flex items-center justify-center text-slate-600"><i data-lucide="image" class="w-4 h-4"></i></div>`
            : `<div class="w-9 h-9 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-600"><i data-lucide="image" class="w-4 h-4"></i></div>`;

        html += `
            <tr class="hover:bg-slate-800/40 transition-colors group cursor-pointer" onclick="openDrawer(${p.id})">
                <td class="py-3 px-4" onclick="event.stopPropagation(); openDrawer(${p.id})">
                    ${imgHtml}
                </td>
                <td class="py-3 px-4 font-mono font-semibold text-blue-400 text-[11px] whitespace-nowrap">
                    ${escapeHtml(p.product_number)}
                </td>
                <td class="py-3 px-4">
                    <div class="font-medium text-slate-200 line-clamp-1 group-hover:text-blue-300 transition-colors" title="${escapeHtml(p.product_name)}">
                        ${escapeHtml(p.product_name)}
                    </div>
                    <div class="text-[11px] text-slate-500 font-mono">
                        ${p.model_number ? escapeHtml(p.model_number) : ''}
                    </div>
                </td>
                <td class="py-3 px-4 text-slate-400 whitespace-nowrap">
                    <div class="text-slate-300">${escapeHtml(p.product_category || '--')}</div>
                    <div class="text-[11px] text-slate-500">${escapeHtml(p.product_sub_category || '')}</div>
                </td>
                <td class="py-3 px-4 text-slate-200">
                    <div class="line-clamp-1 font-medium text-xs text-slate-200" title="${escapeHtml(clf.predicted_category_name || '')}">
                        ${predictedCategory}
                    </div>
                </td>
                <td class="py-3 px-4">
                    <div class="space-y-1">
                        <div class="flex items-center justify-between text-[11px] font-mono font-semibold">
                            <span class="${confidence >= 60 ? 'text-emerald-400' : (confidence > 0 ? 'text-amber-400' : 'text-slate-500')}">${confidence.toFixed(1)}%</span>
                        </div>
                        <div class="confidence-bar-bg">
                            <div class="confidence-bar-fill ${barColor}" style="width: ${confidence}%"></div>
                        </div>
                    </div>
                </td>
                <td class="py-3 px-4">
                    ${statusBadge}
                </td>
                <td class="py-3 px-4 text-right" onclick="event.stopPropagation()">
                    <div class="flex items-center justify-end gap-1.5">
                        <button onclick="openDrawer(${p.id})" class="p-1.5 rounded-lg bg-slate-800 hover:bg-blue-600 hover:text-white text-slate-300 transition-all" title="Review & Override">
                            <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                        </button>
                        <button onclick="quickClassifySingle(${p.id})" class="p-1.5 rounded-lg bg-slate-800 hover:bg-emerald-600 hover:text-white text-slate-300 transition-all" title="Run AI Classifier">
                            <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
    lucide.createIcons();
}

// Update Pagination Info & Buttons
function updatePaginationControls(data) {
    const total = data.count || 0;
    const pageSize = 25;
    const totalPages = Math.ceil(total / pageSize) || 1;

    const from = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const to = Math.min(currentPage * pageSize, total);

    document.getElementById('pagination-from').innerText = from;
    document.getElementById('pagination-to').innerText = to;
    document.getElementById('pagination-total').innerText = total.toLocaleString();
    document.getElementById('pagination-current-page').innerText = `Page ${currentPage} of ${totalPages}`;

    const btnPrev = document.getElementById('btn-prev-page');
    const btnNext = document.getElementById('btn-next-page');

    btnPrev.disabled = !data.previous;
    btnNext.disabled = !data.next;
}

function changePage(delta) {
    const target = currentPage + delta;
    if (target >= 1) {
        fetchProducts(target);
    }
}

// Filter Tab Handler
function setFilter(filterType) {
    currentFilter = filterType;
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('bg-blue-600', 'text-white', 'shadow-sm', 'font-semibold');
        tab.classList.add('text-slate-400', 'font-medium');
    });

    const activeTab = document.getElementById(`filter-tab-${filterType}`);
    if (activeTab) {
        activeTab.classList.add('bg-blue-600', 'text-white', 'shadow-sm', 'font-semibold');
        activeTab.classList.remove('text-slate-400', 'font-medium');
    }

    fetchProducts(1);
}

function clearSearch() {
    const input = document.getElementById('product-search-input');
    input.value = '';
    currentSearch = '';
    document.getElementById('search-clear-btn').classList.add('hidden');
    fetchProducts(1);
}

// Batch Control Logic
async function handleBatchAction(action) {
    const chunkSize = document.getElementById('batch-chunk-size').value;

    try {
        const resp = await fetch('/api/batch/control/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action, chunk_size: parseInt(chunkSize) })
        });

        if (!resp.ok) throw new Error('Action failed');
        const data = await resp.json();

        if (action === 'start' || action === 'resume') {
            showToast('Batch Classification Worker started!', 'success');
            startBatchPolling();
        } else if (action === 'pause') {
            showToast('Batch job paused.', 'warning');
            stopBatchPolling();
        } else if (action === 'reset') {
            showToast('Batch job reset to item 0.', 'info');
            stopBatchPolling();
            fetchMetrics();
            fetchProducts(1);
        }

        updateBatchUI(data.job);
    } catch (e) {
        showToast(`Batch action error: ${e.message}`, 'error');
    }
}

async function checkInitialBatchStatus() {
    try {
        const resp = await fetch('/api/batch/status/');
        if (resp.ok) {
            const job = await resp.json();
            updateBatchUI(job);
            if (job.status === 'RUNNING') {
                startBatchPolling();
            }
        }
    } catch (e) {
        console.error('Error checking batch status:', e);
    }
}

function startBatchPolling() {
    if (batchPollInterval) clearInterval(batchPollInterval);
    batchPollInterval = setInterval(async () => {
        try {
            const resp = await fetch('/api/batch/status/');
            if (!resp.ok) return;
            const job = await resp.json();
            updateBatchUI(job);

            if (job.status === 'COMPLETED') {
                stopBatchPolling();
                showToast('Batch classification fully completed!', 'success');
                fetchMetrics();
                fetchProducts(currentPage);
            } else if (job.status === 'FAILED') {
                stopBatchPolling();
                showToast(`Batch job failed: ${job.error_message}`, 'error');
            } else {
                // Periodically update metrics & table in background
                if (job.processed_items % 100 === 0) {
                    fetchMetrics();
                }
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 1200);
}

function stopBatchPolling() {
    if (batchPollInterval) {
        clearInterval(batchPollInterval);
        batchPollInterval = null;
    }
}

function updateBatchUI(job) {
    if (!job) return;

    const statusBadge = document.getElementById('batch-status-badge');
    const btnStart = document.getElementById('btn-batch-start');
    const btnPause = document.getElementById('btn-batch-pause');
    const btnResume = document.getElementById('btn-batch-resume');
    const progressBar = document.getElementById('batch-progress-bar');
    const progressPct = document.getElementById('batch-progress-pct');
    const progressText = document.getElementById('batch-progress-text');
    const checkpointText = document.getElementById('batch-checkpoint-text');

    const pct = job.progress_percentage || 0;
    progressBar.style.width = `${pct}%`;
    progressPct.innerText = `${pct.toFixed(1)}%`;
    progressText.innerText = `Progress: ${Number(job.processed_items).toLocaleString()} / ${Number(job.total_items).toLocaleString()}`;
    checkpointText.innerText = `Last Checkpoint: Item #${job.last_processed_product_id}`;

    statusBadge.innerText = job.status;
    statusBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border';

    if (job.status === 'RUNNING') {
        statusBadge.classList.add('bg-blue-500/20', 'text-blue-400', 'border-blue-500/30', 'animate-pulse');
        btnStart.classList.add('hidden');
        btnPause.classList.remove('hidden');
        btnResume.classList.add('hidden');
    } else if (job.status === 'PAUSED') {
        statusBadge.classList.add('bg-amber-500/20', 'text-amber-400', 'border-amber-500/30');
        btnStart.classList.add('hidden');
        btnPause.classList.add('hidden');
        btnResume.classList.remove('hidden');
    } else if (job.status === 'COMPLETED') {
        statusBadge.classList.add('bg-emerald-500/20', 'text-emerald-400', 'border-emerald-500/30');
        btnStart.classList.remove('hidden');
        btnPause.classList.add('hidden');
        btnResume.classList.add('hidden');
    } else {
        statusBadge.classList.add('bg-slate-800', 'text-slate-400', 'border-slate-700');
        btnStart.classList.remove('hidden');
        btnPause.classList.add('hidden');
        btnResume.classList.add('hidden');
    }
}

// Quick Classify Single Item
async function quickClassifySingle(productId) {
    try {
        showToast('Running AI classification...', 'info');
        const resp = await fetch(`/api/products/${productId}/classify/`, { method: 'POST' });
        if (!resp.ok) throw new Error('Classification failed');
        const data = await resp.json();
        
        showToast(`Classified as ${data.classification.predicted_category_name}`, 'success');
        fetchMetrics();
        fetchProducts(currentPage);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// Slide-Over Drawer Functions
async function openDrawer(productId) {
    try {
        const resp = await fetch(`/api/products/${productId}/`);
        if (!resp.ok) throw new Error('Failed to load product');
        const p = await resp.json();
        activeDrawerProduct = p;

        document.getElementById('drawer-product-sku').innerText = `SKU: ${p.product_number}`;
        document.getElementById('drawer-product-title').innerText = p.product_name;
        document.getElementById('drawer-source-cat').innerText = p.product_category || '--';
        document.getElementById('drawer-source-subcat').innerText = p.product_sub_category || '--';
        document.getElementById('drawer-msrp').innerText = p.msrp ? `$${Number(p.msrp).toFixed(2)}` : '--';
        document.getElementById('drawer-cost').innerText = p.item_cost ? `$${Number(p.item_cost).toFixed(2)}` : '--';

        const imgEl = document.getElementById('drawer-primary-img');
        const imgPlaceholder = document.getElementById('drawer-img-placeholder');
        if (p.primary_image_url) {
            imgEl.src = p.primary_image_url;
            imgEl.classList.remove('hidden');
            imgPlaceholder.classList.add('hidden');
        } else {
            imgEl.classList.add('hidden');
            imgPlaceholder.classList.remove('hidden');
        }

        const clf = p.classification || {};
        const conf = clf.confidence_score || 0;
        document.getElementById('drawer-confidence-badge').innerText = `${conf.toFixed(1)}% Confidence`;
        document.getElementById('drawer-prediction-name').innerText = clf.predicted_category_name || 'No prediction generated yet';

        const catInput = document.getElementById('drawer-category-input');
        const catId = document.getElementById('drawer-category-id');
        const catGid = document.getElementById('drawer-category-gid');

        catInput.value = clf.predicted_category_name || '';
        catId.value = clf.predicted_category ? clf.predicted_category.id : '';
        catGid.value = clf.predicted_category ? clf.predicted_category.category_gid : '';

        // Render Alternatives
        const altsContainer = document.getElementById('drawer-alternatives-list');
        const alts = clf.alternative_categories || [];
        if (alts.length > 0) {
            document.getElementById('drawer-alternatives-section').classList.remove('hidden');
            let altsHtml = '';
            alts.forEach(alt => {
                altsHtml += `
                    <div class="flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-blue-500/50 transition-all text-xs">
                        <div class="min-w-0 flex-1 mr-2">
                            <p class="font-medium text-slate-200 truncate">${escapeHtml(alt.full_name || alt.name)}</p>
                            <span class="text-[10px] text-purple-400 font-semibold">${alt.confidence}% match</span>
                        </div>
                        <button type="button" onclick="selectAlternative('${alt.category_id || ''}', '${escapeHtml(alt.category_gid || '')}', '${escapeHtml(alt.full_name || alt.name)}')" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-blue-600 text-slate-300 hover:text-white font-semibold text-[11px] transition-colors">
                            Apply
                        </button>
                    </div>
                `;
            });
            altsContainer.innerHTML = altsHtml;
        } else {
            document.getElementById('drawer-alternatives-section').classList.add('hidden');
        }

        // Render Attributes
        renderDrawerAttributes(clf.extracted_attributes || {});

        // Review notes
        document.getElementById('drawer-review-notes').value = clf.review_notes || '';

        // Open Drawer
        document.getElementById('drawer-backdrop').classList.add('active');
        document.getElementById('review-drawer').classList.add('active');
        document.body.style.overflow = 'hidden';

    } catch (e) {
        showToast(e.message, 'error');
    }
}

function closeDrawer() {
    document.getElementById('drawer-backdrop').classList.remove('active');
    document.getElementById('review-drawer').classList.remove('active');
    document.getElementById('drawer-category-dropdown').classList.add('hidden');
    document.body.style.overflow = '';
    activeDrawerProduct = null;
}

function renderDrawerAttributes(attrs) {
    const container = document.getElementById('drawer-attributes-container');
    container.innerHTML = '';

    const entries = Object.entries(attrs);
    if (entries.length === 0) {
        entries.push(['Color', ''], ['Material', ''], ['Assembly Required', 'No']);
    }

    entries.forEach(([key, value]) => {
        addAttributeRow(key, value);
    });
}

function addAttributeRow(key = '', value = '') {
    const container = document.getElementById('drawer-attributes-container');
    const row = document.createElement('div');
    row.className = 'flex items-center gap-2 attr-row';
    row.innerHTML = `
        <input type="text" value="${escapeHtml(key)}" placeholder="Attribute Name" class="attr-key w-1/3 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-semibold focus:outline-none focus:border-blue-500">
        <input type="text" value="${escapeHtml(value)}" placeholder="Attribute Value" class="attr-val flex-1 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500">
        <button type="button" onclick="this.parentElement.remove()" class="p-1.5 text-slate-500 hover:text-rose-400 transition-colors">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
        </button>
    `;
    container.appendChild(row);
    lucide.createIcons();
}

function addNewAttributeField() {
    addAttributeRow('', '');
}

// Category Search & Autocomplete in Drawer
function handleCategorySearch(val) {
    clearTimeout(categorySearchTimeout);
    const dropdown = document.getElementById('drawer-category-dropdown');
    
    if (!val || val.length < 2) {
        dropdown.classList.add('hidden');
        return;
    }

    categorySearchTimeout = setTimeout(async () => {
        try {
            const resp = await fetch(`/api/taxonomy/search/?q=${encodeURIComponent(val)}`);
            if (!resp.ok) return;
            const categories = await resp.json();

            if (categories.length === 0) {
                dropdown.innerHTML = '<div class="p-3 text-xs text-slate-500 text-center">No categories found</div>';
            } else {
                let html = '';
                categories.forEach(c => {
                    html += `
                        <div class="p-2.5 hover:bg-slate-800 cursor-pointer text-xs transition-colors" onclick="selectCategory(${c.id}, '${escapeHtml(c.category_gid)}', '${escapeHtml(c.full_name)}')">
                            <div class="font-semibold text-slate-200">${escapeHtml(c.full_name)}</div>
                            <div class="text-[10px] text-slate-500 font-mono">${escapeHtml(c.category_gid)}</div>
                        </div>
                    `;
                });
                dropdown.innerHTML = html;
            }
            dropdown.classList.remove('hidden');
        } catch (e) {
            console.error(e);
        }
    }, 250);
}

function selectCategory(id, gid, full_name) {
    document.getElementById('drawer-category-input').value = full_name;
    document.getElementById('drawer-category-id').value = id;
    document.getElementById('drawer-category-gid').value = gid;
    document.getElementById('drawer-category-dropdown').classList.add('hidden');
}

function selectAlternative(id, gid, name) {
    document.getElementById('drawer-category-input').value = name;
    document.getElementById('drawer-category-id').value = id;
    document.getElementById('drawer-category-gid').value = gid;
    showToast(`Selected alternative category: ${name}`, 'info');
}

// Save & Approve Classification from Drawer
async function saveDrawerReview() {
    if (!activeDrawerProduct) return;

    const btn = document.getElementById('btn-drawer-approve');
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Saving...</span>`;
    lucide.createIcons();

    // Gather extracted attributes
    const extractedAttributes = {};
    document.querySelectorAll('.attr-row').forEach(row => {
        const k = row.querySelector('.attr-key').value.trim();
        const v = row.querySelector('.attr-val').value.trim();
        if (k) {
            extractedAttributes[k] = v;
        }
    });

    const categoryId = document.getElementById('drawer-category-id').value;
    const categoryName = document.getElementById('drawer-category-input').value.trim();
    const reviewNotes = document.getElementById('drawer-review-notes').value.trim();

    const payload = {
        category_id: categoryId ? parseInt(categoryId) : null,
        category_name: categoryName,
        extracted_attributes: extractedAttributes,
        review_notes: reviewNotes,
        status: 'APPROVED'
    };

    try {
        const resp = await fetch(`/api/products/${activeDrawerProduct.id}/review/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) throw new Error('Failed to save review');
        const data = await resp.json();

        showToast('Product classification approved & saved!', 'success');
        closeDrawer();
        fetchMetrics();
        fetchProducts(currentPage);
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i><span>Approve & Save Classification</span>`;
        lucide.createIcons();
    }
}

// Escape HTML utility
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
