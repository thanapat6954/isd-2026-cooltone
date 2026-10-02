"""Encode independently inspected IT no-coop tables as separate review artifacts."""
import hashlib
import json
import argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,required=True)
    args=parser.parse_args()
    live=args.app_root.resolve()
    source=live/'work/lab8b_it_2560_no_coop/lab7b/pred_vlm.json'
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    booksha=hashlib.sha256((live/'data/input/IT-60.pdf').read_bytes()).hexdigest()
    out=ROOT.parent/'docs/results'
    # Each table was independently viewed, including its printed folio.
    base=json.loads((out/'old2560_it_coop_page36_review.json').read_text(encoding='utf-8'))
    rows29=base['rows']
    rows29[0]['name_en']='PROBABILITY AND STATISTICS'  # Different printed English label from coop PDF36.
    rows30=[
      ('06016309','ความมั่นคงของระบบสารสนเทศและกฎหมายไอที','INFORMATION SYSTEM SECURITY AND IT LAWS','3(3-0-6)',None),
      ('06016310','การออกแบบส่วนต่อประสานกับมนุษย์','HUMAN INTERFACE DESIGN','3(3-0-6)',None),
      ('90304004','การเขียนรายงาน','REPORT WRITING','3(3-0-6)',None),
      ('06016323','การโปรแกรมอุปกรณ์เคลื่อนที่','MOBILE DEVICE PROGRAMMING','3(2-2-5)',1),
      ('06016324','วิศวกรรมความต้องการ','REQUIREMENT ENGINEERING','3(3-0-6)',2),
      ('06016325','การโปรแกรมเชิงบริการ','SERVICE-ORIENTED PROGRAMMING','3(2-2-5)',3),
      ('06016333','เทคโนโลยีการให้บริการอินเตอร์เน็ต','INTERNET SERVICE TECHNOLOGY','3(2-2-5)',1),
      ('06016334','เทคโนโลยีเครือข่ายไร้สาย','WIRELESS NETWORK TECHNOLOGY','3(3-0-6)',2),
      ('06016335','เทคโนโลยีกลุ่มเมฆเบื้องต้น','INTRODUCTION TO CLOUD COMPUTING','3(2-2-5)',3),
      ('06016343','การออกแบบและพัฒนาเกม','GAME DESIGN AND DEVELOPMENT','3(3-0-6)',1),
      ('06016344','หลักการออกแบบกราฟิกส์','GRAPHICS DESIGN PRINCIPLES','3(2-2-5)',2),
      ('06016345','คอมพิวเตอร์แอนิเมชันสามมิติ','3D COMPUTER ANIMATION','3(2-2-5)',3)]
    rows32=[
      ('060163xx','วิชาเลือกทางเทคโนโลยีสารสนเทศ 2','ELECTIVE COURSE IN INFORMATION TECHNOLOGY 2','3(3-0-6) หรือ 3(2-2-5)',None),
      ('90xxxxxx','วิชาเลือกทางมนุษยศาสตร์ 2','ELECTIVE COURSE IN HUMANITY 2','3(3-0-6)',None),
      ('90xxxxxx','วิชาเลือกทางวิทยาศาสตร์กับคณิตศาสตร์ 2','ELECTIVE COURSE IN SCIENTIFIC AND MATHEMATICS 2','3(3-0-6)',None),
      ('xxxxxxxx','วิชาเลือกเสรี 1','FREE ELECTIVE COURSE 1','3(3-0-6)',None),
      ('xxxxxxxx','วิชาเลือกเสรี 2','FREE ELECTIVE COURSE 2','3(3-0-6)',None),
      ('06016329','โครงงานทางด้านวิศวกรรมซอฟต์แวร์ 1','PROJECT IN SOFTWARE ENGINEERING 1','3(0-9-0)',1),
      ('06016339','โครงงานทางด้านเทคโนโลยีเครือข่ายและระบบ 1','PROJECT IN NETWORK AND SYSTEM TECHNOLOGY 1','3(0-9-0)',1),
      ('06016349','โครงงานทางด้านการพัฒนาสื่อประสมและเกม 1','PROJECT IN MULTIMEDIA AND GAME DEVELOPMENT 1','3(0-9-0)',1)]
    rows_y3s2=[
      ('06016307','การบริหารโครงการเทคโนโลยีสารสนเทศ','INFORMATION TECHNOLOGY PROJECT MANAGEMENT','3(3-0-6)',None),
      ('06016318','สัมมนาทางด้านทักษะการสื่อสารในวิชาชีพ','SEMINAR ON PROFESSIONAL COMMUNICATION SKILLS','1(1-0-2)',None),
      ('060163xx','วิชาเลือกทางเทคโนโลยีสารสนเทศ 1','ELECTIVE COURSE IN INFORMATION TECHNOLOGY 1','3(3-0-6) หรือ 3(2-2-5)',None),
      ('06016326','การทวนสอบและตรวจสอบซอฟต์แวร์','SOFTWARE VERIFICATION AND VALIDATION','3(3-0-6)',1),
      ('06016327','การพัฒนาคลาวด์แอปพลิเคชันระดับองค์กร','CLOUD-BASED ENTERPRISE APPLICATION DEVELOPMENT','3(2-2-5)',2),
      ('06016328','เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์','SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS','3(2-2-5)',3),
      ('06016336','การจัดการเครือข่ายและโครงสร้างพื้นฐานเทคโนโลยีสารสนเทศ','NETWORK AND INFORMATION TECHNOLOGY INFRASTRUCTURE MANAGEMENT','3(2-2-5)',1),
      ('06016337','ประสิทธิภาพเครือข่าย','NETWORK PERFORMANCE','3(3-0-6)',2),
      ('06016338','การออกแบบเครือข่ายเบื้องต้น','INTRODUCTION TO NETWORK DESIGN','3(3-0-6)',3),
      ('06016346','การออกแบบและพัฒนาเว็บ','WEB DESIGN AND DEVELOPMENT','3(2-2-5)',1),
      ('06016347','พื้นฐานการเล่าเรื่องและถ่ายภาพยนตร์ดิจิทัล','FUNDAMENTALS OF DIGITAL STORYTELLING AND CINEMATOGRAPHY','3(2-2-5)',2),
      ('06016348','การพัฒนาเกมขั้นสูง','ADVANCED GAME DEVELOPMENT','3(2-2-5)',3)]
    def convert(rows,year,semester):
        return [dict(code=code,name_th=th,name_en=en,credits=credit,
                     **({'alt_group':f'it-specialization-y{year}s{semester}-slot-{slot}'} if slot else {}))
                for code,th,en,credit,slot in rows]
    for page,year,semester,rows in ((29,2,2,rows29),(30,3,1,convert(rows30,3,1)),(32,4,1,convert(rows32,4,1))):
        review={'status':'visually_verified','source_file':'IT-60.pdf','source_sha256':booksha,'input_sha256':sha,
                'pdf_page':page,'printed_page':page-5,'year':year,'semester':semester,'credits':18,'row_count':len(rows),
                'image':f'ocr_final/tmp/pdfs/a1_pages/IT-60-page-{page:03}.png',
                'review_scope':'Entire displayed term table, including all specialization options. No prerequisite/category/type inferred. Separate from frozen OCR.',
                'rows':rows}
        (out/f'old2560_it_no_coop_page{page}_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Reviewed term',page,len(rows))
    for plan,page,year,semester,credit,reviewed_rows in [('no_coop',31,3,2,16,rows_y3s2),('coop',38,3,2,16,rows_y3s2),('coop',37,3,1,18,rows30)]:
        original=live/f'work/lab8b_it_2560_{plan}/lab7b/pred_vlm.json'
        rows=convert(reviewed_rows,year,semester)
        review={'status':'visually_verified','source_file':'IT-60.pdf','source_sha256':booksha,
                'input_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'pdf_page':page,'printed_page':page-5,
                'year':year,'semester':semester,'credits':credit,'row_count':12,'rows':rows,
                'image':f'ocr_final/tmp/pdfs/a1_pages/IT-60-page-{page:03}.png',
                'review_scope':'All twelve displayed options. Common courses plus one three-course specialization bundle; Y3S2 also includes an elective slot. Printed names and credit/hour patterns independently inspected. No prerequisites inferred.'}
        (out/f'old2560_it_{plan}_page{page}_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Reviewed term',plan,page,len(rows))


if __name__=='__main__':main()
