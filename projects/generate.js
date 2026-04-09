const fs = require("fs");
const https = require("https");

const SHEET_ID = "YOUR_SHEET_ID";
const URL = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:json`;

function slugify(text) {
  return text.toString().toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\-]+/g, '')
    .replace(/\-\-+/g, '-')
    .replace(/^-+/, '')
    .replace(/-+$/, '');
}

https.get(URL, (res) => {
  let data = "";

  res.on("data", chunk => {
    data += chunk;
  });

  res.on("end", () => {
    const json = JSON.parse(data.substring(47).slice(0, -2));
    const rows = json.table.rows;

    const talents = rows
      .filter(row => {
        const cells = row.c.map(c => c ? c.v : "");
        return cells[25] !== "非表示";
      })
      .map(row => {
      const cells = row.c.map(c => c ? c.v : "");

      return {
        id: slugify(cells[0]),
        name: cells[1],
        kana: cells[2],
        gender: cells[3],
        age: Number(cells[4]),
        height: Number(cells[5]),
        birthplace: cells[6],
        university: cells[7],
        career: cells[8],
        tags: cells[9] ? cells[9].split(",") : [],
        featured: cells[10] === "true",
        images: cells[11] ? cells[11].split(",") : [],
        social: {
          instagram: cells[12] || "",
          x: cells[13] || ""
        },
        past_projects: cells[14] ? cells[14].split(",") : []
      };
    });

    fs.writeFileSync(
      "assets/data/talents.json",
      JSON.stringify(talents, null, 2),
      "utf8"
    );

    console.log("talents.json generated successfully");
  });
});
