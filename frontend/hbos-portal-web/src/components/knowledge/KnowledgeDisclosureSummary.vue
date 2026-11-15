<template>
  <summary class="kb-disclosure-summary">
    <span class="kb-disclosure-mark" aria-hidden="true">
      <span class="kb-when-closed">＋</span><span class="kb-when-open">−</span>
    </span>
    <span><slot /></span>
    <span class="kb-disclosure-state" aria-hidden="true">
      <span class="kb-when-closed">展开</span><span class="kb-when-open">收起</span>
    </span>
  </summary>
</template>

<style>
.kb-disclosure-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  cursor: pointer;
  list-style: none;
}
.kb-disclosure-summary::-webkit-details-marker { display: none; }
.kb-disclosure-mark {
  display: inline-grid;
  place-items: center;
  flex: 0 0 22px;
  height: 22px;
  border-radius: 6px;
  background: #efeaff;
  color: #5144bd;
}
.kb-disclosure-state { flex: none; margin-inline-start: auto; color: #596b84; font-size: 12px; white-space: nowrap; }
.kb-disclosure-summary .kb-when-open,
details[open] > .kb-disclosure-summary .kb-when-closed { display: none; }
details[open] > .kb-disclosure-summary .kb-when-open { display: inline; }
</style>
