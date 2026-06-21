# magicicapsula
<img width="512" height="512" alt="image" src="https://github.com/user-attachments/assets/db00444f-3795-45f1-8176-3f26aaa64498" />

## install

```
pip install magicicapsula
```

needs python 3.10+. one dependency: `cryptography`.

## how it works

the workflow is staged, so you don't have to add everything at once:

```
magicicapsula init -u 2030-01-01     # start a draft here
magicicapsula add letter.txt photos/ # stage files/folders
magicicapsula add diary.txt          # add more later
magicicapsula status                 # see what's staged
magicicapsula seal                   # pack it all into capsule.mcap
```

the draft lives in a `.capsule/` directory (found by walking up from the
current dir). `seal` reads everything staged and writes the `.mcap` file.

later, when the date has passed:

```
magicicapsula open capsule.mcap -d ./out
```

`.mcap` is one portable binary file. store it anywhere, copy it around. it
holds any file type (images, pdfs, binaries) byte for byte, not just text.

## passwords

- with a password (default): contents are encrypted (aes-128 via `cryptography`),
  unreadable without the password. `open` and `verify` prompt for it.
- without a password (`seal --no-password`): no encryption. the unlock date is
  the only gate, so anyone with the file can open it after that date. don't put
  anything private in a no-password capsule.

note: the unlock date is enforced by the tool, not by cryptography. if you hold
the password you could decrypt early with other means. the date stops casual
early opening, not a determined holder.

## commands

### init
start a new capsule draft in the current directory.

```
magicicapsula init [-u DATE] [-n NOTE] [-o OUT]

  -u, --unlock DATE  unlock date, can also be set at seal
  -n, --note NOTE    plaintext note shown by info
  -o, --out OUT      output file name (default: capsule.mcap)
```

### add
stage files or folders to put in the capsule.

```
magicicapsula add <paths...>
```

### status
show the draft: unlock date and staged files.

```
magicicapsula status
```

### rm
unstage files. does not delete them from disk.

```
magicicapsula rm <paths...>
```

### seal
seal everything staged into a capsule file. flags override the draft's
settings and stick.

```
magicicapsula seal [-u DATE] [-o FILE] [-n NOTE] [-f] [-P]

  -u, --unlock DATE  unlock date, overrides the draft's
  -o, --out FILE     output capsule file, overrides the draft's
  -n, --note NOTE    plaintext note, overrides the draft's
  -f, --force        overwrite the output if it exists
  -P, --no-password  seal without a password (anyone can open it after the date)
```

### info
show a capsule's dates and status. no password needed.

```
magicicapsula info <file>
```

### open
open a capsule and extract it, once the unlock date has passed.

```
magicicapsula open [-d DEST] <file>

  -d, --dest DEST  directory to extract into (default: current dir)
```

### verify
check a capsule's integrity (and the password, if any) without opening it.

```
magicicapsula verify <file>
```

### version
show the version and logo.

```
magicicapsula version
```

## date format

`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`, read as local time. examples:
`2030-01-01`, `2030-01-01T08:00`.

## colors

output is colored in a terminal and plain when piped or redirected. set
`NO_COLOR=1` to turn colors off.

## dates and gotchas

- staged entries are paths, read at seal time, not copied when you add them.
  if a staged file is moved or deleted before sealing, `status` marks it
  `(missing)` and `seal` refuses until it's fixed.
- files are stored under their base name, so two staged files with the same
  name would collide.
