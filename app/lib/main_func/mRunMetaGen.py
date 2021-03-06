from app.lib.run.MAIN_PROCESS import process as MP
from app.lib.run.Assembly import idbaud as idba
import os,re
from app.lib.common import module
from app.lib.common import rootvar
import json
import networkx as nx
from networkx.readwrite import json_graph
import numpy as np
#from app.lib.run import MAIN_PROCESS as MP
from app.lib.create_project import insert_new_project as sql
from app.lib.preprocessing import functions as pre
import os
import logging

def my_logger(logfile=''):
    main_logfile = logfile
    logging.basicConfig(
        filename=main_logfile,
        level=logging.DEBUG,
        filemode="w",
        format="%(levelname)s %(asctime)s - %(message)s"
    )

    return logging.getLogger()

def run(data,main_db,DBS):
    project_id=str(data['pid'])
    pipeline=str(data['pip'])
    reads1=str(data['read1'])
    reads2=str(data['read2'])
    sample_id=str(data['sid'])
    user_id=str(data['uid'])
    refs=data["rids"]
    try:
        a=refs[0]
    except:
        return 'Error: No database has been selected'

    x=sql.SQL(main_db)
    x.exe('UPDATE project_status SET status="queue" WHERE project_id="'+project_id+'" AND sample_id="'+sample_id+'"')
    x.insert("sample_run",(sample_id,"created")) # let know that the files have been uploaded and the files created
    x.commit()
    #preprocessing FIXME: I need to get permisions to write
    rdir=rootvar.__ROOTPRO__+"/"+project_id+"/READS/"
    trim=pre.trimmomatic(rdir+reads1,rdir+reads2,rdir,sample_id)
    #if not rootvar.isdir(trim.outd+sample_id+'.trim.log'): trim.run()
    trim.run()
    #print "trimming"
    reads1=reads1.replace(".gz","")
    reads2=reads2.replace(".gz","")
    #print pipeline
    ##################################################################################################
    ##### This is very important,
    ##### First: Check if the GREENGENES database has been used for finding the 16s rRNAs, if not,
    ##### The greengenes database is force d to run this database will run first for normalization purposes.
    ##################################################################################################
    if pipeline=="assembly": greengenes_file=rootvar.__ROOTPRO__+"/"+project_id+"/assembly/idba_ud/"+sample_id+"/pred.genes.Gbfbquhild.matches"
    if pipeline=="matches": greengenes_file=rootvar.__ROOTPRO__+"/"+project_id+"/matches/"+sample_id+"/pred.genes.Gbfbquhild.matches"
    #_______________________________________________________________##################################
    #
    # Get the number of reads
    tfile=trim.outd+sample_id+'trim.log'
    for i in open(tfile):
        if "Input Read Pairs:" in i:
            i=i.split()
            raw_reads=float(i[3])
            good_reads=float(i[6]) # the number of high quality reads after trimming and quality filter
    print good_reads

    if pipeline == "matches":
        log = my_logger(logfile=rootvar.__ROOTPRO__+"/"+project_id+"/matches/"+sample_id+"/arc_run.qsub.log")
        log.info('running read match pipeline')
        for ref in refs:
            log.info('Processing %s with reference id: %s'%(sample_id, ref) )
            if not x.exe('select * from matches where sample_id="'+sample_id+'" and datasets="'+ref+'"'):
                x.c.execute('INSERT OR IGNORE INTO matches VALUES (?,?,?,?)', (sample_id,user_id,project_id,ref))
                x.commit()
            try:
                val = MP(project_id, sample_id, DBS[ref], "matches", reads1, reads2, good_reads)
            except Exception as e:
                log.error(str(e))
                log.error('Exception\t%s\t%s'%(sample_id, ref))
    #
    #this is for the aseembly section
    #
    if pipeline=="assembly":
        log = my_logger(logfile=rootvar.__ROOTPRO__ + "/" + project_id + "/assembly/idba_ud/" + sample_id + "/arc_run.qsub.log")
        log.info('running assembly pipeline')
        for ref in refs:
            log.info('Processing %s with reference id: %s'%(sample_id, ref) )
            if not x.exe('select * from assembly where sample_id="'+sample_id+'" and datasets="'+ref+'"'):
                x.c.execute('INSERT OR IGNORE INTO assembly VALUES (?,?,?,?)', (sample_id,user_id,project_id,ref))
                x.commit()
            try:
                idba(project_id, sample_id, DBS[ref], "assembly", reads1, reads2, good_reads)
            except Exception as e:
                log.error(str(e))
                log.error('Exception\t%s\t%s' % (sample_id, ref))

    x.close()
    # in the end the fastq files need to be removed in order to save storage space;
    if not rootvar.isdir(rdir+reads1+".gz"):
        os.system('gzip '+rdir+reads1+' >> '+rootvar.log+" 2>&1")
        os.system('rm '+rdir+reads1+' >> '+rootvar.log+" 2>&1")
    else:
        os.system('rm '+rdir+reads1+' >> '+rootvar.log+" 2>&1")

    if not rootvar.isdir(rdir+reads2+".gz"):
        os.system('gzip '+rdir+reads2+' >> '+rootvar.log+" 2>&1")
        os.system('rm '+rdir+reads2+' >> '+rootvar.log+" 2>&1")
    else:
        os.system('rm '+rdir+reads2+' >> '+rootvar.log+" 2>&1")

    return 'success'










