import unicodedata
import re
from copy import copy
import pandas as pd
from joblib import Parallel, delayed
import time


from ..config import TARGET_PATH, WORKING_PATH, DATA_PATH
from ..config import LINKS_PATH, LIST_RESULTS, STUFF_PATH
from ..config import GRAPH_PATH, ensuredir

from .results import ResultsBoundingBoxes
from .db import TheoremDB,Paper,loadLinks
from ..ml.features import process_paper

IDX_TO_PAPER = STUFF_PATH +"/ref_identifiants.csv"
LIST_RESULTS.extend(["thm.","lem.","prop."])
dico_abreviations = {   'thm.' : 'theorem',
                        'lem.' : 'lemma',
                        'prop.': 'proposition'}

# Normalize text, for instance when we have ﬁ instead of fi
def normalize(text):
    text = re.sub(r'(\w)-\s+(\w)',r'\1\2',text)
    return  unicodedata.normalize("NFKD",text)

# Merge the dictionnary obtained with Sementic Scholar and the one created on our own
'''
The dictionnary 1 is more exact but have less elements.
'''
def merge_dicos(d1,d2):
    d = d1.copy()
    err,pok = 0,0
    for k in d2.keys():
        if k in d1:
            # We test the dictionnary 2
            c_ok = 0
            c_tot = 0
            pap = {d1[k][j]: j  for j in d1[k]}
            pap2 = {d2[k][j]: j for j in d2[k]}
            for p in pap:
                if p in pap2:
                    c_tot += 1
                    if pap[p] == pap2[p]:
                        c_ok += 1
            if c_tot > 0 and c_ok/c_tot < 0.5:
                err += 1
                continue
            pok +=1
            for j in d2[k]:
                if j not in d1[k]:
                    d[k][j] = d2[k][j]
        else:
            d[k] = d2[k]
    print("Errors : %i \n OK : %i"%(err,pok))
    return d

# Extract references found with grobid
def extract_refs(filepath):
    df = pd.read_csv(filepath,dtype=str)
    dico_pdf = {}
    for _,row in df.iterrows():
        pdfname = row.source
        identifiant = re.sub(r'\W','',row.identifiant)
        if pdfname not in dico_pdf.keys():
            dico_pdf[pdfname] = {}

        if type(row.target) == str:
            dico_pdf[pdfname][identifiant] = row.target

    return dico_pdf

# Find the name of the result.
def find_thm_start(text):
    try:
        t = re.match(r'((open )?(\w+) ([a-z]\.)?[\d]+(\.\d+)*)',text,re.IGNORECASE)
        return t[0]
    except:
        ()#print("ERROR :",text)

# Find if this is a proof of a particular theorem (e.g. "proof of Theorem 5.2")
def find_thm_proof(text):
    precise = re.search(r'Proof. \[([^\]]+)\]',text,re.IGNORECASE)
    if precise == None:
        return None
    res = re.search(r'((\w+) ([a-z]\.)?[\d]+(\.\d+)*)',precise[1],re.IGNORECASE)
    if res == None:
        return None
    return res[0]

# Find references to other results inside a paragraph
def find_ref_results(thm,text):
    if thm == None:
        thm = ""
    results = re.findall(r'((%s)(s)? (([a-z]\.)?[\d]+(\.\d+)*(#in)?(\s?(and|,|&) ([a-z]\.)?[\d]+(\.\d+)*(#in)?)*))'%("|".join(LIST_RESULTS)),
                        text,
                        re.IGNORECASE)
    
    res = [re.sub('#in','',r[0]) for r in results]
    res_type = [r[1] for r in results]
    is_mul = [r[8] for r in results]
    seen = []
    intraref = []
    extraref = []

    for i,r in enumerate(res):
        if r in seen or r.lower() == thm.lower():
            continue
        seen.append(r)

        # Find every occurence of the particular result r
        context = re.findall(r'(((\S+ ){0,5}(\S*)?)(%s)(#in)?((?!(\.\d+|\d+))(\S*)( \S+){0,5}))'%r,text)
        for c in context:
            if c[5] == '#in':
                if res_type[i][-1] == '.':
                    nums = re.findall(r'(([a-z]\.)?[\d]+(\.\d+)*)',r,re.IGNORECASE)
                    intraref.extend([dico_abreviations[res_type[i].lower()]+' '+num[0] 
                            for num in nums])
                elif is_mul[i] != "":
                    nums = re.findall(r'(([a-z]\.)?[\d]+(\.\d+)*)',r,re.IGNORECASE)
                    intraref.extend([res_type[i]+' '+num[0] for num in nums])
                else:
                    intraref.append(c[4].lower())
                continue	
            context_full = c[0]
            context_before_split = c[1].split(" ")[:-1]
            context_after_split = c[6].split(" ")[1:]
            refto = None
            # We take the closest link in a range +/- 5 around the results referenced
            for dist in range(5):
                if dist < len(context_before_split):
                    refto = re.match(r'<LINK:([^>]+)>',context_before_split[-1-dist])
                    if refto != None:
                        break
                if dist < len(context_after_split):
                    refto = re.match(r'<LINK:([^>]+)>',context_after_split[dist])
                    if refto != None:
                        break
            
            # If a link is found...
            if refto != None:
                refto = re.sub(r'\W','',refto[1])
                if refto == re.sub(r'\W','',r) or re.search(r'((%s)([a-z])?[\d]+)'%("|".join(LIST_RESULTS+["section","algorithm"])),refto,re.IGNORECASE):
                    if res_type[i][-1] == '.':
                        nums = re.findall(r'(([a-z]\.)?[\d]+(\.\d+)*)',r,re.IGNORECASE)
                        intraref.extend([dico_abreviations[res_type[i].lower()]+' '+num[0] 
                                for num in nums])
                    elif is_mul[i] != "":
                        nums = re.findall(r'(([a-z]\.)?[\d]+(\.\d+)*)',r,re.IGNORECASE)
                        intraref.extend([res_type[i]+' '+num[0] for num in nums])
                    else:					
                        intraref.append(c[4].lower())
                else:
                    if res_type[i][-1] == '.':
                        nums = re.findall(r'(([a-z]\.)?[\d]+(\.\d+)*)',r,re.IGNORECASE)
                        extraref.extend([(refto,dico_abreviations[res_type[i].lower()]+' '+num[0]) 
                                for num in nums])
                    elif is_mul[i] != "":
                        nums = re.findall(r'(([a-z]\.)?[\d]+(\.\d+)*)',r,re.IGNORECASE)
                        extraref.extend([(refto,res_type[i]+' '+num[0]) for num in nums])
                    else:
                        extraref.append((refto,c[4].lower()))
            # Otherwise...
            else:
                if res_type[i][-1] == '.':
                    nums = re.findall(r'(([a-z]\.)?[\d]+(\.\d+)*)',r,re.IGNORECASE)
                    intraref.extend([dico_abreviations[res_type[i].lower()]+' '+num[0] 
                            for num in nums])
                elif is_mul[i] != "":
                    nums = re.findall(r'(([a-z]\.)?[\d]+(\.\d+)*)',r,re.IGNORECASE)
                    intraref.extend([res_type[i]+' '+num[0] for num in nums])
                else:
                    intraref.append(c[4].lower())

    return res,intraref,extraref

# df -> results list
def extract_results(paper):
        paper_theorems = {}
        df = process_paper(paper,mode="word")
        if type(df) == type(None):
            return None

        bbox = paper.results
        curr_result = -1
        link_on = False
        link_kind = "Text"

        for _,row in df.iterrows():
            # We are going out of one result
            if row.kind[0] == "O" and curr_result >= 0:
                if link_on >= 0:
                    paper_theorems[curr_result]['text'] += ">"
                    link_on = -1
                curr_result = -1
            # We are in a result
            elif row.kind[0] != "O":
                new_result = row.result
                # We are going out of the previous one
                if curr_result >= 0 and new_result != curr_result:
                    if link_on:
                        paper_theorems[curr_result]['text'] += ">"
                        link_on = -1
                # This is a new result
                if new_result not in paper_theorems:
                    paper_theorems[new_result] = {"cat":row.kind[2:],
                                                "text":row.text}
                    link_on = -1
                # This is not a new result
                else:
                    # This is a link
                    if row.is_link >= 0:
                        # The same than before
                        if link_on == row.is_link:
                            if link_kind != "Text":
                                new_text = re.sub("(([a-z]\.)?\d+(\.\d+)*)",r"\1#in",row.text,re.IGNORECASE)
                                paper_theorems[new_result]['text'] += " "+new_text
                            else:
                                paper_theorems[new_result]['text'] += ""+row.text
                        # A new link
                        else:
                            node = {"PHYSICAL_IMG_NR":row.page_dest,
                                "HPOS":float(row.x_dest),
                                "VPOS":float(row.y_dest)+10,
                                "WIDTH":0,
                                "HEIGHT":0}
                            # Detect if the link go to a result inside the paper
                            kind, n_ref = bbox.get_kind(node,kind="point",extend_size=20)
                            # If there were no link before...
                            if link_on < 0:
                                if kind == "Text":
                                    paper_theorems[new_result]['text'] += " <LINK:"+row.text
                                else:
                                    paper_theorems[new_result]['text'] += " "+ row.text
                            # If there were another link before...
                            else:
                                if link_kind == "Text":
                                    paper_theorems[new_result]['text'] += ">"
                                if kind == "Text":
                                    paper_theorems[new_result]['text'] += " <LINK:"+row.text
                                else:
                                    new_text = re.sub("(([a-z]\.)?\d+(\.\d+)*)",r"\1#in",row.text,re.IGNORECASE)
                                    paper_theorems[new_result]['text'] += " "+new_text

                            link_on = row.is_link
                            link_kind = kind

                    # This is not a link but there was a link previously
                    elif row.is_link < 0 and link_on >=0:
                        if link_kind == "Text":
                            paper_theorems[new_result]['text'] += "> "+row.text
                        link_on = -1
                    
                    # Otherwise...
                    else:
                        paper_theorems[new_result]['text'] += " "+row.text
                curr_result = new_result	


        for n in paper_theorems:
            cat = paper_theorems[n]["cat"]
            text = paper_theorems[n]["text"]
            text = normalize(text)
            if cat != "proof":
                thm = find_thm_start(text)
            else:
                thm = "Proof"
            paper_theorems[n] = (thm,text)

        
        return paper_theorems

# results list -> links list
def extract_links(dico_pdf,thms,pdfname):

    thmRefs = {}
    n2res = {}
    outRefs = {}
    outRes = []
    lastThm = ""

    out_links = []
    out_res = []

    for n in thms.keys():

        thm, txt = thms[n]
        if thm == "Proof":
            theoremProved = find_thm_proof(txt)

            # If it is not a "Proof of theorem X" we automatically assign it to the last theorem seen
            if not(theoremProved):
                theoremProved = lastThm

            n2res[n] = theoremProved
            outRes.append(theoremProved)

            # Get refs
            results,intras,extras = find_ref_results(theoremProved,txt)
            if theoremProved not in thmRefs:
                thmRefs[theoremProved] = []
            thmRefs[theoremProved].extend(results)

        else:
            lastThm = thm
            outRes.append(thm)
            results,intras,extras = find_ref_results(thm,txt)
            thmRefs[thm] = results
            n2res[n] = thm

        intras = list(set(intras))
        extras = list(set(extras))
        
        # Results intra paper
        for thm in intras:
            out_links.append((pdfname,n,n2res[n],thm,True,None,pdfname))

        # Results extra paper
        for ref,thm in extras:
            if dico_pdf == None or (ref not in dico_pdf):
                out_links.append((pdfname,n,n2res[n],thm,False,ref,None))
            else:
                out_links.append((pdfname,n,n2res[n],thm,False,ref,dico_pdf[ref]))

    
    outRes = list(set(outRes))

    for res in outRes:
        out_res.append((pdfname,res))
        

    return out_res,out_links

# paper -> results and links
def get_results_list_paper(paper,dico_pdf):
    results = extract_results(paper)
    if results == None:
        return None, None
    return extract_links(dico_pdf,results,paper.id)

# Save array
def save_graph(name,df_out_res,df_out_links):
    df_out_res = pd.DataFrame(df_out_res)
    df_out_res.to_csv(GRAPH_PATH+"/graph_results_%s.csv"%name,
                    index=False,
                    header=["pdf_from","result"])

    df_out_links = pd.DataFrame(df_out_links)
    df_out_links.to_csv(GRAPH_PATH+"/graph_intra_extra_%s.csv"%name,
                        index=False,
                        header=["pdf_from","nres_in","theorem_in","theorem_ref","intra","ref_tag","pdf_to"])

# global function with all papers in //
def get_results_list(thmdb,dico_pdf,name,multithreading=True,n_jobs=4,chunks_size=1000):
    keys = thmdb.papers.keys()
    papers_thms = {}
    out_res = []
    out_links = []

    if multithreading:

        paper_list = []
        for k in keys:
            if k not in dico_pdf:
                dico_pdf_i = None
            else:
                dico_pdf_i = dico_pdf[k]
            paper_list.append((thmdb.papers[k],dico_pdf_i))

        n_paper = len(paper_list)
        n_chunks = (n_paper-1) // chunks_size + 1
        for chunk in range(n_chunks):
            print("Chunk %i/%i"%(chunk+1,n_chunks))
            results_mt= Parallel(n_jobs=n_jobs)(delayed(get_results_list_paper)(paper,dico) 
                                        for paper,dico in paper_list[chunk*chunks_size:(chunk+1)*chunks_size])
            for i in range(len(results_mt)):
                out_res_i,out_links_i = results_mt[i]
                paper = paper_list[i]

                if out_res_i == None:
                    continue
                
                out_res.extend(out_res_i)
                out_links.extend(out_links_i)
            save_graph(name,out_res,out_links)
            print("Saved")
    else:
        for k in keys:
            paper = thmdb.papers[k]
            out_res_i,out_links_i = get_results_list_paper(paper)
            out_res.extend(out_res_i)
            out_links.extend(out_links_i)
        save_graph(name,out_res,out_links)


# Main fonction
def extract_graph(name,multithreading=True,n_jobs=4,chunks_size=1000):

    print("Extract refs...")
    t0 = time.time()

    dico_pdf = extract_refs(IDX_TO_PAPER)
    dico_pdf_2 = ll.load(True)
    dico_pdf = merge_dicos(dico_pdf,dico_pdf_2)

    t1 = time.time()
    print("Get db...")

    thmdb = TheoremDB(merge_all=True)

    t2 = time.time()
    print("Get results and links...")

    get_results_list(thmdb,
                    dico_pdf,
                    name,
                    multithreading=multithreading,
                    n_jobs=n_jobs,
                    chunks_size=chunks_size)

    t3 = time.time()
    print("Extract dictionnary (constant) : %.2f"%(t1-t0))
    print("Get papers (linear) : %.2f"%(t2-t1))
    print("Get results (linear) : %.2f"%(t3-t2))


