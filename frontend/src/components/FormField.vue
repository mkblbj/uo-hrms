<template>
	<div v-if="showField" class="flex flex-col gap-1.5">
		<!-- Label -->
		<span
			v-if="!['Check', 'Section Break', 'Column Break'].includes(props.fieldtype)"
			:class="[
				// mark field as mandatory
				props.reqd ? `after:content-['_*'] after:text-red-600` : ``,
				`block text-sm leading-5 text-gray-700`,
			]"
		>
			{{ props.label }}
		</span>

		<!-- Select or Link field with predefined options -->
		<Combobox
			v-if="props.fieldtype === 'Select' || props.documentList"
			trigger="button"
			:placeholder="__('Select {0}', [props.label])"
			:options="selectionList"
			:model-value="modelValue ?? null"
			:hide-search="props.hideSearch"
			v-bind="$attrs"
			:disabled="isReadOnly || $attrs.disabled === '' || Boolean($attrs.disabled)"
			@update:model-value="(value) => emit('update:modelValue', value ?? '')"
		>
			<template #suffix="{ clear, disabled: isDisabled, open }">
				<span
					v-if="modelValue !== '' && modelValue != null && !isDisabled"
					role="button"
					tabindex="0"
					:aria-label="__('Clear {0}', [props.label])"
					class="inline-flex rounded-2 p-1 text-gray-600 hover:text-gray-900 focus-visible:outline focus-visible:outline-2"
					@click.stop.prevent="clear()"
					@keydown.enter.stop.prevent="clear()"
					@keydown.space.stop.prevent="clear()"
					@keyup.enter.stop.prevent
					@keyup.space.stop.prevent
				>
					<Icon icon="lucide-x" class="h-4 w-4" aria-hidden="true" />
				</span>
				<Icon
					icon="lucide-chevron-down"
					:class="['h-4 w-4 shrink-0 text-gray-600 transition-transform', open && 'rotate-180']"
					aria-hidden="true"
				/>
			</template>
		</Combobox>

		<!-- Link field -->
		<Link
			v-else-if="props.fieldtype === 'Link'"
			:doctype="props.options"
			:modelValue="modelValue"
			:filters="props.linkFilters"
			:disabled="isReadOnly || $attrs.disabled === '' || Boolean($attrs.disabled)"
			@update:modelValue="(v) => emit('update:modelValue', v)"
		/>

		<TextEditor
			v-else-if="props.fieldtype === 'Text Editor'"
			:content="modelValue"
			:placeholder="__('Enter {0}', [props.label])"
			@change="(v) => emit('update:modelValue', v)"
			:fixedMenu="true"
			:editable="!isReadOnly"
			editor-class="prose-sm border-b border-x border-gray-200 rounded-b-1 p-1 min-h-[4rem]"
		/>

		<!-- Text -->
		<Textarea
			v-else-if="['Small Text', 'Text', 'Long Text'].includes(props.fieldtype)"
			:model-value="modelValue"
			:placeholder="__('Enter {0}', [props.label])"
			@update:model-value="(v) => emit('update:modelValue', v)"
			v-bind="$attrs"
			:disabled="isReadOnly"
			class="h-15"
		/>

		<!-- Check -->
		<Checkbox
			v-else-if="props.fieldtype === 'Check'"
			:label="props.label"
			:model-value="modelValue"
			@update:model-value="(v) => emit('update:modelValue', v)"
			v-bind="$attrs"
			:disabled="isReadOnly"
			class="rounded-1 text-gray-800"
		/>

		<!-- Data field -->
		<TextInput
			v-else-if="props.fieldtype === 'Data'"
			type="text"
			:model-value="modelValue"
			@update:model-value="(v) => emit('update:modelValue', v)"
			v-bind="$attrs"
			:disabled="isReadOnly"
		/>

		<!-- Read only currency field -->
		<TextInput
			v-else-if="props.fieldtype === 'Currency' && isReadOnly"
			type="text"
			:model-value="modelValue"
			@update:model-value="(v) => emit('update:modelValue', v)"
			v-bind="$attrs"
			:disabled="isReadOnly"
		/>

		<!-- Float/Int field -->
		<TextInput
			v-else-if="isNumberType"
			type="number"
			:model-value="modelValue"
			@update:model-value="(v) => emit('update:modelValue', v)"
			v-bind="$attrs"
			:disabled="isReadOnly"
		/>

		<!-- Section Break -->
		<div
			v-else-if="props.fieldtype === 'Section Break'"
			:class="props.addSectionPadding ? 'mt-2' : ''"
		>
			<h2
				v-if="props.label"
				class="text-base-semibold text-gray-800"
				:class="props.addSectionPadding ? 'pt-4' : ''"
			>
				{{ props.label }}
			</h2>
		</div>

		<!-- Date -->
		<!-- FIXME: default datepicker has poor UI -->
		<TextInput
			v-else-if="props.fieldtype === 'Date'"
			type="date"
			:model-value="modelValue"
			:placeholder="__('Select {0}', [props.label])"
			:formatValue="(val) => dayjs(val).format('DD-MM-YYYY')"
			@update:model-value="(v) => emit('update:modelValue', v)"
			v-bind="$attrs"
			:disabled="isReadOnly"
			:min="props.minDate"
			:max="props.maxDate"
		/>

		<!-- Time -->
		<!-- Datetime -->
		<input
			v-else-if="props.fieldtype === 'Datetime' && props.nativeDateTime"
			type="datetime-local"
			:value="nativeDateTimeValue"
			:placeholder="__('Select {0}', [props.label])"
			@input="updateNativeDateTime"
			@change="changeNativeDateTime"
			v-bind="$attrs"
			:disabled="isReadOnly"
			class="form-input block w-full rounded-4 border-gray-400 placeholder-gray-500"
		/>
		<DateTimePicker
			v-else-if="props.fieldtype === 'Datetime'"
			:model-value="modelValue"
			:placeholder="__('Select {0}', [props.label])"
			:formatter="props.dateTimeFormatter || ((val) => dayjs(val).format('DD-MM-YYYY HH:mm:ss'))"
			@update:modelValue="(v) => emit('update:modelValue', v)"
			v-bind="$attrs"
			:disabled="isReadOnly"
		/>

		<ErrorMessage :message="props.errorMessage" />
	</div>
</template>

<script setup>
import {
	Combobox,
	DateTimePicker,
	ErrorMessage,
	TextInput,
	Textarea,
	Checkbox,
	Icon,
} from "frappe-ui"
import { TextEditor } from "frappe-ui/experimental"
import { computed, onMounted, inject } from "vue"

import Link from "@/components/Link.vue"

const __ = inject("$translate")

const props = defineProps({
	fieldtype: String,
	fieldname: String,
	modelValue: [String, Number, Boolean, Array, Object],
	default: [String, Number, Boolean, Array, Object],
	label: String,
	options: [String, Array],
	linkFilters: Object,
	documentList: Array,
	dateTimeFormatter: Function,
	nativeDateTime: Boolean,
	toNativeDateTimeValue: Function,
	fromNativeDateTimeValue: Function,
	readOnly: [Boolean, Number],
	reqd: [Boolean, Number],
	hidden: {
		type: [Boolean, Number],
		default: false,
	},
	errorMessage: String,
	minDate: String,
	maxDate: String,
	addSectionPadding: {
		type: Boolean,
		default: true,
	},
	hideSearch: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(["change", "update:modelValue"])
const dayjs = inject("$dayjs")

const showField = computed(() => {
	if (props.readOnly && !isLayoutField.value && !props.modelValue) return false

	return props.fieldtype !== "Table" && !props.hidden
})

const isNumberType = computed(() => {
	return ["Int", "Float", "Currency"].includes(props.fieldtype)
})

const isLayoutField = computed(() => {
	return ["Section Break", "Column Break"].includes(props.fieldtype)
})

const isReadOnly = computed(() => {
	return Boolean(props.readOnly)
})

const nativeDateTimeValue = computed(() => {
	if (props.toNativeDateTimeValue) return props.toNativeDateTimeValue(props.modelValue)
	const match = String(props.modelValue || "").match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})/)
	return match ? `${match[1]}T${match[2]}:${match[3]}` : ""
})

function normalizeNativeDateTimeValue(value) {
	if (props.fromNativeDateTimeValue) return props.fromNativeDateTimeValue(value)
	if (!value) return ""
	const match = String(value).match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/)
	return match ? `${match[1]} ${match[2]}:${match[3]}:00` : String(value)
}

function updateNativeDateTime(event) {
	emit("update:modelValue", normalizeNativeDateTimeValue(event.target.value))
}

function changeNativeDateTime(event) {
	const value = normalizeNativeDateTimeValue(event.target.value)
	emit("update:modelValue", value)
	emit("change", value)
}

const selectionList = computed(() => {
	if (props.documentList) {
		return props.documentList
	} else if (props.fieldtype == "Select" && props.options) {
		const options = props.options.split("\n")
		return options.map((option) => ({
			label: __(option),
			value: option,
		}))
	}

	return []
})

function setDefaultValue() {
	// set default values
	if (props.modelValue) return

	if (props.default) {
		if (props.fieldtype === "Check") {
			emit("update:modelValue", props.default === "1" ? true : false)
		} else if (props.fieldtype === "Date" && props.default === "Today") {
			emit("update:modelValue", dayjs().format("YYYY-MM-DD"))
		} else if (isNumberType.value) {
			emit("update:modelValue", parseFloat(props.default || 0))
		} else {
			emit("update:modelValue", props.default)
		}
	} else {
		props.fieldtype === "Check" ? emit("update:modelValue", false) : emit("update:modelValue", "")
	}
}

onMounted(() => {
	setDefaultValue()
})
</script>
