/**
 * Paste into the browser console while viewing a Goodreads shelf list
 * page you're logged into, e.g.:
 *
 *   https://www.goodreads.com/review/list/<your_user_id>?shelf=read&per_page=200
 *
 * First turn on the "Date started" and "Date read" columns for the
 * table (the small settings/gear control above the header row lets you
 * pick which columns show) - the scrape only reads what's visibly
 * rendered in the row.
 *
 * Prints CSV to the console and copies it to the clipboard. Run once
 * per shelf you care about (typically "read" and "did-not-finish" -
 * Goodreads' main export doesn't include either shelf's start dates at
 * all, which is why this exists) and concatenate the outputs (keeping
 * only one header line) into a single CSV before passing it to
 * apply_goodreads_start_dates.py.
 *
 * If a shelf has more books than one page shows, bump per_page (up to
 * 200) or page through with &page=2, &page=3, ... and concatenate.
 */
(function () {
  function csvField(s) {
    s = (s || "").trim();
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  const rows = document.querySelectorAll("tr.bookalike.review");
  if (!rows.length) {
    console.warn(
      "No rows found - make sure you're on a Goodreads shelf list page " +
        "(.../review/list/<id>?shelf=...) and it's finished loading."
    );
    return;
  }

  const lines = ["title,author,date_started,date_read"];
  rows.forEach((row) => {
    const title = row.querySelector(".field.title a")?.textContent || "";
    const author = row.querySelector(".field.author a")?.textContent || "";
    const dateStarted =
      row.querySelector(".field.date_started .date_started_value")
        ?.textContent || "";
    const dateRead =
      row.querySelector(".field.date_read .date_read_value")?.textContent ||
      "";
    lines.push([title, author, dateStarted, dateRead].map(csvField).join(","));
  });

  const csv = lines.join("\n");
  console.log(csv);
  try {
    copy(csv); // Chrome/Firefox devtools console helper
    console.log(`\n${rows.length} rows copied to clipboard.`);
  } catch (e) {
    console.log(`\n${rows.length} rows - copy() unavailable, use the console output above.`);
  }
})();
