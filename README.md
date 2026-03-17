Various scripts to handle email.

## Tools

- **mbox2html** - Convert MIME email with inline images to a self-contained
  HTML file. Replaces cid: references with inline base64 data URIs.
  Useful for viewing HTML email with embedded images in a browser from mutt.

  ```
  mbox2html msg.eml > out.html
  mbox2html -o out.html msg.eml
  mbox2html -b firefox msg.eml
  mbox2html -b xdg-open msg.eml   # use default browser
  ```
