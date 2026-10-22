const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

function loadReport(mobile = false, canWrite = true) {
  const copied = [];
  const dialogs = [];
  const calls = [];
  const employee = {
    doctype: "Employee",
    name: "EMP-'001",
    employee_name: "张三",
    modified: "2026-10-16 15:00:00.000000",
    status: "Active",
    user_id: "login@example.com",
    cell_number: "09001234567",
    custom_wechat_id: "wx_00123",
    current_address: "東京都\n建物 101",
    company_email: "",
    personal_email: "personal@example.com",
    person_to_be_contacted: "李四",
    relation: "配偶",
    emergency_phone_number: "09000001234",
  };
  let handler;
  const escape = (text) =>
    String(text ?? "").replace(
      /[&<>"']/g,
      (char) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        }[char])
    );
  const frappe = {
    query_reports: {},
    model: { can_write: () => canWrite },
    call: async (options) => {
      calls.push(options);
      if (options.method === "frappe.client.get")
        return { message: { ...employee } };
      return { message: JSON.parse(options.args.doc) };
    },
    show_alert() {},
    utils: {
      escape_html: escape,
      copy_to_clipboard: (value) => copied.push(value),
    },
    ui: {
      Dialog: class {
        constructor(options) {
          this.options = options;
          dialogs.push(this);
        }
        show() {
          this.shown = true;
        }
        hide() {
          this.shown = false;
        }
      },
    },
  };
  const report = {
    refreshCount: 0,
    async refresh() {
      this.refreshCount++;
    },
    data: [
      {
        name: "EMP-'001",
        employee_name: "<b>张三</b>",
        cell_number: "09001234567",
        custom_wechat_id: "wx_00123",
        current_address: "東京都\n<div>建物 101</div>",
      },
    ],
    $report: {
      off() {
        return this;
      },
      on(event, selector, fn) {
        handler = fn;
        return this;
      },
    },
  };
  vm.runInNewContext(
    readFileSync(join(__dirname, "employee_information_overview.js"), "utf8"),
    {
      frappe,
      __: (value) => value,
      window: { matchMedia: () => ({ matches: mobile }) },
    }
  );
  const settings = frappe.query_reports["Employee Information Overview"];
  return {
    settings,
    report,
    copied,
    dialogs,
    calls,
    employee,
    frappe,
    click: (dataset) =>
      handler({
        currentTarget: { dataset },
        preventDefault() {},
        stopPropagation() {},
      }),
  };
}

function format(settings, field, value, row = { name: "EMP-'001" }) {
  return settings.formatter(value, null, { fieldname: field }, row, (text) =>
    String(text ?? "")
  );
}

test("name opens the original employee and escapes user text", () => {
  const { settings } = loadReport();
  const html = format(
    settings,
    "employee_name",
    '<img src=x onerror="alert(1)">'
  );
  assert.ok(html.includes("/app/employee/"));
  assert.ok(html.includes("&lt;img"));
  assert.ok(!html.includes("<img"));
  assert.ok(!html.includes('href="/app/employee/EMP-\'001"'));
});

test("missing phone and address are explicit; optional WeChat uses a dash", () => {
  const { settings } = loadReport();
  assert.ok(format(settings, "cell_number", " \t ").includes("Not provided"));
  assert.ok(format(settings, "current_address", null).includes("Not provided"));
  assert.ok(format(settings, "custom_wechat_id", "").includes("—"));
});

test("phone and WeChat copy raw text without losing leading zeros", () => {
  const { settings, report, copied, click } = loadReport();
  settings.onload(report);
  for (const field of ["cell_number", "custom_wechat_id"]) {
    click({ employee: "EMP-'001", contactField: field });
  }
  assert.deepEqual(copied, ["09001234567", "wx_00123"]);
});

test("address opens full escaped multiline text and copies the original", () => {
  const { settings, report, copied, dialogs, click } = loadReport();
  settings.onload(report);
  click({ employee: "EMP-'001", contactField: "current_address" });
  assert.equal(dialogs.length, 1);
  assert.equal(dialogs[0].shown, true);
  const field = dialogs[0].options.fields[0];
  assert.ok(field.options.includes("white-space: pre-wrap"));
  assert.ok(field.options.includes("&lt;div&gt;"));
  dialogs[0].options.primary_action();
  assert.deepEqual(copied, [report.data[0].current_address]);
});

test("status is translated and all plain text cells escape HTML", () => {
  const { settings } = loadReport();
  assert.ok(format(settings, "status", "Active").includes("Employed"));
  assert.ok(format(settings, "status", "Left").includes("Former Employee"));
  assert.ok(
    !format(settings, "employee_number", "<script>alert(1)</script>").includes(
      "<script>"
    )
  );
});

test("filters default to active employees and omit the branch filter", () => {
  const { settings } = loadReport();
  const filters = new Map(
    settings.filters.map((filter) => [filter.fieldname, filter])
  );
  for (const field of [
    "search",
    "status",
    "company",
    "department",
    "missing_phone",
    "missing_address",
  ]) {
    assert.ok(filters.has(field));
  }
  assert.equal(filters.get("status").default, "Active");
  assert.ok(!filters.has("branch"));
  assert.ok(!filters.get("company").default);
});

test("contact buttons escape both content and employee attributes", () => {
  const { settings } = loadReport();
  const html = format(
    settings,
    "custom_wechat_id",
    '"><script>alert(1)</script>',
    { name: 'EMP-" onclick="alert(1)' }
  );
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.includes('data-employee="EMP-" onclick='));
});

test("mobile keeps room to scroll contact columns while desktop fixes the employee ID", () => {
  for (const mobile of [true, false]) {
    const { settings } = loadReport(mobile);
    const columns = [
      { id: "employee_name", colIndex: 1, sticky: true },
      { id: "name", colIndex: 2, sticky: true },
    ];
    settings.after_datatable_render({
      datamanager: { getColumns: () => columns },
      columnmanager: {
        setColumnSticky: (index, sticky) => {
          columns.find((column) => column.colIndex === index).sticky = sticky;
        },
      },
    });
    assert.equal(columns[0].sticky, true);
    assert.equal(columns[1].sticky, !mobile);
  }
});

test("quick edit is available beside employee names only with write permission", () => {
  const editable = loadReport();
  assert.ok(
    format(editable.settings, "employee_name", "张三").includes(
      "data-edit-employee"
    )
  );
  const readonly = loadReport(false, false);
  assert.ok(
    !format(readonly.settings, "employee_name", "张三").includes(
      "data-edit-employee"
    )
  );
});

test("quick edit loads fresh contact fields and saves the original employee with its version", async () => {
  const { settings, report, calls, dialogs, click, employee } = loadReport();
  settings.onload(report);
  await click({ editEmployee: employee.name });
  assert.equal(calls[0].method, "frappe.client.get");
  assert.equal(calls[0].args.name, employee.name);
  const dialog = dialogs[0];
  const fields = new Map(
    dialog.options.fields.map((field) => [field.fieldname, field])
  );
  for (const name of [
    "cell_number",
    "custom_wechat_id",
    "current_address",
    "company_email",
    "personal_email",
    "person_to_be_contacted",
    "relation",
    "emergency_phone_number",
  ]) {
    assert.equal(fields.get(name).default, employee[name]);
  }
  assert.equal(fields.get("account_email").default, "login@example.com");
  assert.ok(fields.get("account_email").read_only);
  const values = {
    cell_number: "+81-90-0000-0000",
    custom_wechat_id: "wx_new",
    current_address: "大阪府\n新住所",
    company_email: "work@example.com",
    personal_email: "new@example.com",
    person_to_be_contacted: "王五",
    relation: "兄弟",
    emergency_phone_number: "+81-80-0000-0000",
    user_id: "attacker@example.com",
    status: "Left",
  };
  await dialog.options.primary_action(values);
  const saved = JSON.parse(calls[1].args.doc);
  assert.equal(calls[1].method, "frappe.client.save");
  for (const name of [
    "cell_number",
    "custom_wechat_id",
    "current_address",
    "company_email",
    "personal_email",
    "person_to_be_contacted",
    "relation",
    "emergency_phone_number",
  ])
    assert.equal(saved[name], values[name]);
  assert.equal(saved.modified, employee.modified);
  assert.equal(saved.user_id, employee.user_id);
  assert.equal(saved.status, "Active");
  assert.equal(dialog.shown, false);
  assert.equal(report.refreshCount, 1);
});

test("failed quick edit keeps the dialog and unsaved values available", async () => {
  const { settings, report, dialogs, click, employee, frappe } = loadReport();
  settings.onload(report);
  await click({ editEmployee: employee.name });
  frappe.call = async () => {
    throw new Error("Permission denied");
  };
  await assert.rejects(
    dialogs[0].options.primary_action({}),
    /Permission denied/
  );
  assert.equal(dialogs[0].shown, true);
  assert.equal(report.refreshCount, 0);
});
