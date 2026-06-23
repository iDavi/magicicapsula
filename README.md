# MAGICICADA !!!!!!
<img width="932" height="718" alt="image" src="https://github.com/user-attachments/assets/bf9ab92c-4933-42d6-8941-3accdf392a51" />

# magicicapsula
<img width="512" height="512" alt="image" src="https://github.com/user-attachments/assets/db00444f-3795-45f1-8176-3f26aaa64498" />

## install

```
pip install magicicapsula
```

needs python 3.10+

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
magicicapsula add --text "dear future me" [--name letter.txt]
echo "..." | magicicapsula add -

  --text TEXT  stage text directly, no file needed
  --name NAME  filename for --text or stdin (default: note.txt)
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

### remind
write a calendar (`.ics`) reminder for a capsule's unlock date. no account
or api needed: import the file into any calendar (google, apple, outlook).

```
magicicapsula remind <file> [-o FILE] [-b DAYS] [-f]

  -o, --out FILE    output .ics path (default: <capsule>.ics)
  -b, --before DAYS remind this many days before the unlock date
  -f, --force       overwrite the output if it exists
```

### version

```
magicicapsula version
```

## date format

absolute `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM` (`2030-01-01`, `2030-01-01T08:00`),
or relative from now: `+30d`, `+2w`, `+6m`, `+1y`.

