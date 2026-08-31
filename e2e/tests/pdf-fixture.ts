export function multiPagePdfFixture(): Buffer {
  const padding = "% M15 byte-range fixture data; no private content.\n".repeat(
    3000,
  );
  const firstStream = Buffer.from(
    `BT /F1 16 Tf 72 720 Td (M15 literature page one) Tj ET\n${padding}`,
    "ascii",
  );
  const secondStream = Buffer.from(
    "BT /F1 16 Tf 72 720 Td (M15 literature page two) Tj ET\n",
    "ascii",
  );
  const streamObject = (stream: Buffer) =>
    Buffer.concat([
      Buffer.from(`<< /Length ${stream.length} >>\nstream\n`, "ascii"),
      stream,
      Buffer.from("endstream", "ascii"),
    ]);
  const objects = [
    Buffer.from("<< /Type /Catalog /Pages 2 0 R >>", "ascii"),
    Buffer.from("<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>", "ascii"),
    Buffer.from(
      "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] " +
        "/Resources << /Font << /F1 7 0 R >> >> /Contents 4 0 R >>",
      "ascii",
    ),
    streamObject(firstStream),
    Buffer.from(
      "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] " +
        "/Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>",
      "ascii",
    ),
    streamObject(secondStream),
    Buffer.from(
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
      "ascii",
    ),
  ];

  let output = Buffer.from("%PDF-1.4\n", "ascii");
  const offsets = [0];
  for (const [index, object] of objects.entries()) {
    offsets.push(output.length);
    output = Buffer.concat([
      output,
      Buffer.from(`${index + 1} 0 obj\n`, "ascii"),
      object,
      Buffer.from("\nendobj\n", "ascii"),
    ]);
  }
  const xrefOffset = output.length;
  const xref = [
    `xref\n0 ${objects.length + 1}\n`,
    "0000000000 65535 f \n",
    ...offsets
      .slice(1)
      .map((offset) => `${offset.toString().padStart(10, "0")} 00000 n \n`),
    `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\n`,
    `startxref\n${xrefOffset}\n%%EOF\n`,
  ].join("");
  return Buffer.concat([output, Buffer.from(xref, "ascii")]);
}
