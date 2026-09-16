<template>
	<Combobox
		ref="comboboxRef"
		size="sm"
		trigger="button"
		v-model="value"
		v-model:query="query"
		:placeholder="__('Select {0}', [__(doctype)])"
		:options="options.data || []"
		:loading="options.loading"
		:filterable="false"
		:disabled="disabled"
		@update:query="handleQueryUpdate"
		@update:open="handleOpenUpdate"
	>
		<template #suffix="{ clear, disabled: isDisabled, open }">
			<span
				v-if="value && !isDisabled"
				role="button"
				tabindex="0"
				:aria-label="__('Clear {0}', [__(doctype)])"
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
</template>

<script setup>
import { createResource, Combobox, debounce, Icon } from "frappe-ui"
import { ref, computed, watch, onBeforeUnmount } from "vue"

import {
	handleLinkOpenUpdate,
	resetLinkSearchState,
} from "@/utils/selectionControlState"

const props = defineProps({
	doctype: {
		type: String,
		required: true,
	},
	modelValue: {
		type: String,
		required: false,
		default: "",
	},
	filters: {
		type: Object,
		default: {},
	},
	disabled: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(["update:modelValue"])

const comboboxRef = ref(null)
const query = ref("")
const searchText = ref("")

const value = computed({
	get: () => props.modelValue,
	set: (val) => {
		if (typeof val === "string") {
			emit("update:modelValue", val)
		} else {
			emit("update:modelValue", val?.value || "")
		}
	},
})

const options = createResource({
	url: "frappe.desk.search.search_link",
	params: {
		doctype: props.doctype,
		txt: searchText.value,
		filters: props.filters,
	},
	method: "POST",
	transform: (data) => {
		const mapped = data.map((doc) => {
			let title = null
			if (doc.label && doc.label !== doc.value){
				title = doc.label
			} else if (doc.description) {
				title = doc.description.split(",")[0]
			}
			return {
				label: title ? `${title} : ${doc.value}` : doc.value,
				value: doc.value,
			}
		})

		if (props.modelValue && !mapped.find((o) => o.value === props.modelValue)) {
			mapped.unshift({ label: props.modelValue, value: props.modelValue })
		}
		return mapped
	},
})

const reloadOptions = (searchTextVal) => {
	options.abort()
	options.update({
		params: {
			txt: searchTextVal,
			doctype: props.doctype,
			filters: props.filters,
		},
	})
	options.reload()
}

const handleQueryUpdate = debounce((newQuery) => {
	const val = newQuery || ""
	if (searchText.value === val) return
	searchText.value = val
	reloadOptions(val)
}, 300)

const resetSearch = () => {
	resetLinkSearchState({
		query,
		searchText,
		cancelPendingSearch: handleQueryUpdate.cancel,
		reloadOptions,
	})
}

const handleOpenUpdate = (isOpen) => {
	handleLinkOpenUpdate(isOpen, resetSearch)
}

watch(
	() => props.doctype,
	() => {
		if (!props.doctype) return
		resetSearch()
	},
	{ immediate: true }
)

watch(
	() => props.filters,
	() => resetSearch(),
	{ deep: true }
)

watch(
	() => props.modelValue,
	(newVal, oldVal) => {
		if (!newVal && oldVal) {
			// value cleared — reload so the dropdown shows the full default list
			resetSearch()
		} else if (newVal && newVal !== oldVal) {
			// reload so transform can inject it if it's outside the default page
			const inOptions = (options.data || []).find((o) => o.value === newVal)
			if (options.data && !inOptions) resetSearch()
		}
	}
)

onBeforeUnmount(() => {
	handleQueryUpdate.cancel()
	options.abort()
})
</script>
