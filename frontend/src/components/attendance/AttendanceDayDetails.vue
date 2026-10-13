<template>
	<div v-if="loading" class="detail-loading" role="status" aria-live="polite">
		<p>{{ copy("detail.loading") }}</p>
		<div class="detail-skeleton" aria-hidden="true" />
	</div>
	<div v-else-if="error" class="detail-error" role="alert">
		<p>{{ copy("detail.loadError") }}</p>
		<button type="button" @click="$emit('retry')">{{ copy("detail.retry") }}</button>
	</div>
	<div v-else-if="details" class="day-details">
		<section class="detail-total" :aria-label="copy('detail.totalHours')">
			<div class="detail-total-label">{{ copy("detail.totalHours") }}</div>
			<div class="detail-total-value">
				<strong>{{
					pending ? copy("detail.pending") : formatDetailHours(details.working_hours)
				}}</strong>
				<span v-if="details.is_settled" class="detail-hours-unit">h</span>
			</div>
			<p v-if="pending" class="detail-completed">
				{{ copy("detail.completed") }} <b>{{ formatDetailHours(details.completed_hours) }} h</b>
			</p>
		</section>
		<p v-if="details.has_total_difference" class="detail-difference" role="status">
			{{ copy("detail.totalDifference") }}
		</p>

		<section :aria-label="copy('detail.periods')">
			<h3 class="detail-section-title">{{ copy("detail.periods") }}</h3>
			<ol class="detail-period-list">
				<li
					v-for="(period, index) in details.periods"
					:key="`${period.in_time}-${index}`"
					class="detail-period"
				>
					<div class="detail-period-heading">
						<h4>{{ copy("detail.period", { index: index + 1 }) }}</h4>
						<strong>{{ formatDetailHours(period.working_hours) }} <span>h</span></strong>
					</div>
					<dl class="detail-period-punches">
						<div>
							<dt>{{ copy("detail.checkIn") }}</dt>
							<dd>{{ clock(period.in_time) }}</dd>
						</div>
						<div>
							<dt>{{ copy("detail.checkOut") }}</dt>
							<dd>{{ clock(period.out_time) }}</dd>
						</div>
					</dl>
					<div class="detail-counted">
						<span>{{ copy("detail.countedTime") }}</span>
						<b v-if="period.counted_time_empty">{{ copy("detail.shortPeriod") }}</b>
						<b v-else
							>{{ clock(period.counted_in_time) }} — {{ clock(period.counted_out_time) }}</b
						>
					</div>
					<div class="detail-counted">
						<span>{{ copy("detail.lunch") }}</span>
						<b>{{ formatDetailHours(period.lunch_deduction) }} h</b>
					</div>
				</li>
				<li v-if="details.open_period" class="detail-period detail-period-open">
					<div class="detail-period-heading">
						<h4>{{ copy("detail.period", { index: details.periods.length + 1 }) }}</h4>
						<span>{{ copy("detail.openPeriod") }}</span>
					</div>
					<div class="detail-counted">
						<span>{{ copy("detail.checkIn") }}</span
						><b>{{ clock(details.open_period.in_time) }}</b>
					</div>
				</li>
			</ol>
			<p v-if="!details.periods.length && !details.open_period" class="detail-empty">
				{{ copy("detail.noPeriods") }}
			</p>
		</section>

		<section :aria-label="copy('detail.punches')">
			<h3 class="detail-section-title">
				{{ copy("detail.punches") }} <span>{{ details.checkins.length }}</span>
			</h3>
			<ol class="detail-punch-list">
				<li v-for="punch in details.checkins" :key="punch.name" class="detail-punch">
					<div class="detail-punch-label">
						<span :class="['detail-punch-type', { 'detail-punch-in': punch.log_type === 'IN' }]">{{
							copy(
								punch.log_type === "IN"
									? "detail.checkIn"
									: punch.log_type === "OUT"
									? "detail.checkOut"
									: "detail.punch"
							)
						}}</span>
						<span
							v-if="punch.checkin_method === 'Attendance Correction'"
							class="detail-punch-note"
							>{{ copy("detail.correctionPunch") }}</span
						>
						<span v-if="!punch.included_in_calculation" class="detail-punch-note">{{
							copy("detail.excluded")
						}}</span>
					</div>
					<time :datetime="String(punch.time).replace(' ', 'T')">{{
						clock(punch.time, true)
					}}</time>
				</li>
			</ol>
			<p v-if="!details.checkins.length" class="detail-empty">{{ copy("detail.noPunches") }}</p>
		</section>
	</div>
</template>

<script setup>
import { computed } from "vue"
import { getAttendanceCopy } from "@/utils/attendanceCalendarCopy"
import { formatDetailHours, formatDetailTime } from "@/utils/attendanceDayDetails"

const props = defineProps({
	details: { type: Object, default: null },
	loading: { type: Boolean, default: false },
	error: { default: null },
	lang: { type: String, default: "zh" },
})
defineEmits(["retry"])
const copy = (key, params = {}) => getAttendanceCopy(key, props.lang, params)
const clock = (value, seconds = false) =>
	formatDetailTime(value, props.details.attendance_date, seconds)
const pending = computed(() => !props.details?.is_settled && props.details?.checkins?.length > 0)
</script>

<style scoped>
.day-details {
	display: grid;
	gap: 16px;
	margin-top: 12px;
}
.detail-total {
	padding: 14px 16px;
	border: 1px solid var(--h-bd-default);
	border-radius: 12px;
	background: var(--h-bg-card-inner);
}
.detail-total-label {
	color: var(--h-fg-secondary);
	font-size: 12px;
	font-weight: 600;
}
.detail-total-value {
	display: flex;
	align-items: baseline;
	gap: 6px;
	margin-top: 4px;
	color: var(--h-fg-primary);
	font-variant-numeric: tabular-nums;
}
.detail-total-value strong {
	font-size: 28px;
	letter-spacing: -0.03em;
	line-height: 1.2;
}
.detail-hours-unit {
	font-size: 15px;
	color: var(--h-fg-secondary);
}
.detail-completed {
	margin: 8px 0 0;
	font-size: 12px;
	color: var(--h-fg-secondary);
}
.detail-completed b {
	margin-left: 6px;
	color: var(--h-fg-primary);
}
.detail-section-title {
	display: flex;
	align-items: center;
	gap: 8px;
	margin: 0 0 8px;
	font-size: 13px;
	font-weight: 700;
	color: var(--h-fg-primary);
}
.detail-section-title span {
	color: var(--h-fg-secondary);
	font-size: 12px;
	font-weight: 500;
}
.detail-period-list,
.detail-punch-list {
	list-style: none;
	margin: 0;
	padding: 0;
}
.detail-period-list {
	display: grid;
	gap: 8px;
}
.detail-period {
	padding: 12px;
	border: 1px solid var(--h-bd-default);
	border-radius: 12px;
}
.detail-period-heading {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 8px;
}
.detail-period-heading h4 {
	margin: 0;
	font-size: 13px;
	color: var(--h-fg-primary);
}
.detail-period-heading strong {
	font-size: 18px;
	color: var(--h-attn-work-fg);
	font-variant-numeric: tabular-nums;
}
.detail-period-heading strong span {
	font-size: 12px;
	font-weight: 500;
}
.detail-period-punches {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
	margin: 10px 0;
}
.detail-period-punches dt {
	color: var(--h-fg-secondary);
	font-size: 12px;
}
.detail-period-punches dd {
	margin: 3px 0 0;
	font-size: 15px;
	color: var(--h-fg-primary);
	font-variant-numeric: tabular-nums;
}
.detail-counted {
	display: flex;
	justify-content: space-between;
	flex-wrap: wrap;
	gap: 4px 8px;
	margin-top: 4px;
	color: var(--h-fg-secondary);
	font-size: 12px;
	line-height: 1.5;
}
.detail-counted b {
	color: var(--h-fg-primary);
	font-weight: 500;
	font-variant-numeric: tabular-nums;
}
.detail-period-open {
	border-style: dashed;
	background: var(--h-bg-card-inner);
}
.detail-period-open .detail-period-heading > span {
	color: var(--h-fg-secondary);
	font-size: 12px;
}
.detail-punch {
	display: flex;
	align-items: center;
	justify-content: space-between;
	flex-wrap: wrap;
	gap: 6px 8px;
	padding: 10px 0;
	border-bottom: 1px solid var(--h-bd-subtle);
}
.detail-punch:last-child {
	border-bottom: 0;
}
.detail-punch-label {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 6px;
}
.detail-punch-type {
	color: var(--h-fg-primary);
	font-size: 13px;
	font-weight: 600;
}
.detail-punch-in {
	color: var(--h-attn-work-fg);
}
.detail-punch-note {
	color: var(--h-fg-secondary);
	font-size: 11px;
	border: 1px solid var(--h-bd-default);
	border-radius: 4px;
	padding: 1px 4px;
}
.detail-punch time {
	font-size: 13px;
	font-variant-numeric: tabular-nums;
	color: var(--h-fg-primary);
}
.detail-empty {
	margin: 0;
	font-size: 13px;
	line-height: 1.5;
	color: var(--h-fg-secondary);
}
.detail-difference,
.detail-error {
	padding: 12px;
	border-radius: 10px;
	font-size: 13px;
	background: var(--h-attn-anomaly-bg);
	color: var(--h-attn-anomaly-fg);
}
.detail-difference {
	margin: 0;
}
.detail-loading {
	margin-top: 12px;
	font-size: 13px;
	color: var(--h-fg-secondary);
}
.detail-loading p,
.detail-error p {
	margin: 0 0 8px;
}
.detail-skeleton {
	height: 100px;
	border-radius: 12px;
	background: var(--h-bg-card-inner);
	border: 1px solid var(--h-bd-default);
}
.detail-error {
	margin-top: 12px;
}
.detail-error button {
	min-height: 44px;
	padding: 0 16px;
	background: var(--h-bg-card);
	border: 1px solid var(--h-bd-default);
	border-radius: 8px;
	color: var(--h-fg-primary);
	font-weight: 600;
}
.detail-error button:focus-visible {
	outline: 2px solid var(--h-attn-work-fg);
	outline-offset: 2px;
}
</style>
