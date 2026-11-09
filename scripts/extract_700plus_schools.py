import re, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
src = openpyxl.load_workbook('Aslam_School_Report.xlsx')['Visited (1st visit)']
rows = list(src.iter_rows(values_only=True)); hdr, data = rows[0], rows[1:]
idx = {h:i for i,h in enumerate(hdr)}
def parse(s):
    if s is None: return None, None
    t = str(s).strip()
    m = re.fullmatch(r'(\d+)\s*[-+]?', t)
    if m: return int(m.group(1)), 'exact'
    m = re.fullmatch(r'(?:below|blow|<)\s*(\d+)|(\d+)\s*below', t, re.I)
    if m: return int(m.group(1) or m.group(2)), 'below'
    m = re.fullmatch(r'(\d+)/(\d+)', t)
    if m: return int(m.group(2)), 'range'
    return None, 'unknown'
main, border = [], []
for r in data:
    n, kind = parse(r[idx['Strength']])
    if n is None: continue
    if kind == 'exact' and n >= 700: main.append((n, r))
    elif kind in ('below','range') and n > 700 or (kind=='range' and n>=700): border.append((n, r))
main.sort(key=lambda x:(-x[0], x[1][0], x[1][2])); border.sort(key=lambda x:(-x[0], x[1][0]))
cols = ['Area','School','Type','Contact person','Contact no.','Strength (as recorded)','Students','First visit','Visits','Call remarks','Probability','In Deepika data']
F = 'Arial'; hf = Font(name=F,bold=True,color='FFFFFF'); fill = PatternFill('solid',fgColor='1F4E78')
thin = Side(style='thin',color='BFBFBF'); bd = Border(left=thin,right=thin,top=thin,bottom=thin)
widths = [14,46,14,28,26,14,10,12,22,60,12,30]
wb = openpyxl.Workbook()
def sheet(ws, title, note, items):
    ws['A1'] = title; ws['A1'].font = Font(name=F,bold=True,size=14)
    ws['A2'] = note; ws['A2'].font = Font(name=F,italic=True,size=9,color='595959')
    for j,c in enumerate(cols,1):
        x = ws.cell(4,j,c); x.font=hf; x.fill=fill; x.alignment=Alignment(wrap_text=True,vertical='center'); x.border=bd
        ws.column_dimensions[get_column_letter(j)].width = widths[j-1]
    for i,(n,r) in enumerate(items,5):
        vals = [r[idx['Area']],r[idx['School']],r[idx['Type']],r[idx['Contact person']],r[idx['Contact no.']],str(r[idx['Strength']]),n,r[idx['First visit']],r[idx['Visits']],r[idx['Call remarks']],r[idx['Probability']],r[idx['In Deepika data']]]
        for j,v in enumerate(vals,1):
            x = ws.cell(i,j,v); x.font=Font(name=F,size=10); x.border=bd
            x.alignment=Alignment(vertical='top',wrap_text=(j in (2,10)))
    ws.freeze_panes='A5'; ws.auto_filter.ref=f'A4:{get_column_letter(len(cols))}{4+len(items)}'
    return 4+len(items)
ws = wb.active; ws.title = 'Schools 700+'
last = sheet(ws, f"Aslam - Visited Schools with 700+ Students ({len(main)})",
  "Source: Aslam_School_Report.xlsx, sheet 'Visited (1st visit)', Strength column. Includes recorded strength >= 700 (e.g. '700', '800-', '800+'), sorted highest first.", main)
ws2 = wb.create_sheet('Borderline (check)')
sheet(ws2, f"Borderline - strength recorded as a range/upper limit ({len(border)})",
  "Not included in main list: strength written as 'Below X' / '<X' / 'X/Y' with X > 700, so actual count may or may not exceed 700. Verify by phone.", border)
# summary with formulas
s = wb.create_sheet('Summary by Area', 0)
s['A1']='Schools with 700+ Students - Summary by Area'; s['A1'].font=Font(name=F,bold=True,size=14)
for j,h in enumerate(['Area','Schools 700+','Total students (700+ schools)','Borderline (check)'],1):
    x=s.cell(3,j,h); x.font=hf; x.fill=fill; x.border=bd; x.alignment=Alignment(wrap_text=True)
areas = sorted({r[0] for _,r in main+border})
M="'Schools 700+'"; B="'Borderline (check)'"
for i,a in enumerate(areas,4):
    s.cell(i,1,a)
    s.cell(i,2,f'=COUNTIF({M}!$A$5:$A${last},A{i})')
    s.cell(i,3,f'=SUMIF({M}!$A$5:$A${last},A{i},{M}!$G$5:$G${last})')
    s.cell(i,4,f'=COUNTIF({B}!$A$5:$A$500,A{i})')
t = 4+len(areas); s.cell(t,1,'TOTAL')
for j,c in ((2,'B'),(3,'C'),(4,'D')): s.cell(t,j,f'=SUM({c}4:{c}{t-1})')
for row in s.iter_rows(min_row=4,max_row=t):
    for x in row: x.font=Font(name=F,size=10,bold=(x.row==t)); x.border=bd
    row[2].number_format='#,##0'
for c,w in zip('ABCD',(18,14,22,18)): s.column_dimensions[c].width=w
wb.save('Aslam_Schools_700plus_Students.xlsx')
print(len(main), len(border), sum(1 for n,_ in main if n==700))
