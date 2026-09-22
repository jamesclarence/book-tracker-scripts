/*
 * Pulls per-item checkout dates off a Koha OPAC "Checkout history" page
 * (opac-readingrecord.pl), without clicking through every row.
 *
 * Why this works: Koha renders that page's table with jQuery DataTables
 * using its "Responsive" extension. On a narrow viewport it hides a
 * "Date" column and only reveals it per-row when you click the little
 * "+" control - but the data for EVERY row (including the hidden
 * column) is already loaded into the DataTable's in-memory model. This
 * reads that model directly instead of clicking 200+ "+" buttons.
 *
 * Usage: open the checkout-history page (?limit=full shows everything,
 * not just the last 50), open the browser console, and paste this in.
 * It logs one line per kept item as "Title <TAB> Item type <TAB> Date"
 * (date is either MM/DD/YYYY for a returned item, or the literal string
 * "(Checked out)" for one that's still out).
 *
 * Requires jQuery + DataTables to already be on the page, which is the
 * case for Koha's default OPAC theme - no extra libraries needed.
 */

(function () {
  function stripHtml(s) {
    const d = document.createElement("div");
    d.innerHTML = s || "";
    return (d.textContent || "").replace(/\s+/g, " ").trim();
  }

  const KEEP_ITEM_TYPES = { "Book": 1, "Book - Paperback": 1, "Audiobook on CD": 1 };

  const dt = jQuery("table.dataTable").DataTable();
  const rows = dt.rows().data();
  const out = [];

  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    // Column indices match Koha's default checkout-history table layout:
    // [type icon, expand control, Title, Author, Item type, Call number, Vol info, Date, (control)]
    const itemType = stripHtml(r[4]);
    if (!KEEP_ITEM_TYPES[itemType]) continue;

    const title = stripHtml(r[2]).replace(/\s*\/\s*$/, "").replace(/\.$/, "").trim();
    const dateCell = r[7];
    const dateVal = dateCell && dateCell.display ? stripHtml(dateCell.display) : stripHtml(dateCell);

    out.push(title + "\t" + itemType + "\t" + dateVal);
  }

  console.log(out.join("\n"));
  window.__checkoutData = out; // also stash it so you can slice/copy it further
  console.log(`\n${out.length} rows captured (see window.__checkoutData)`);
})();
