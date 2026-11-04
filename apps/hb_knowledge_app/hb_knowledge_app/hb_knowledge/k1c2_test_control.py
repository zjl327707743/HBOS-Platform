"""Owner-only CLI for registered synthetic mutations; NOT a whitelisted HTTP API."""
import frappe
from .k1c2_migration import guard
def mutate(kind,target,value):
    guard()
    if kind in {'enabled','roles'}:
        if not target.endswith('@k1c2.invalid') or not frappe.db.exists('User',target):
            frappe.throw('Unregistered synthetic user')
        if kind=='enabled':
            if type(value) is not int or value not in (0,1): frappe.throw('Bad mutation')
            frappe.db.set_value('User',target,'enabled',value,update_modified=False)
        else:
            if not isinstance(value,list) or any(r not in {'K1C2 QA','K1C2 Shared','K1C2 Production'} for r in value): frappe.throw('Bad roles')
            frappe.db.delete('Has Role',{'parent':target,'parenttype':'User'})
            for role in value:
                # Direct persisted role facts deliberately do not flush warmed caches.
                row=frappe.get_doc({'doctype':'Has Role','role':role,'parent':target,'parenttype':'User','parentfield':'roles'})
                row.db_insert()
    elif kind=='binding':
        if target not in {'BINDING_QA_A','BINDING_SHARED_B','BINDING_PROD'} or value not in (0,1): frappe.throw('Bad binding')
        frappe.db.set_value('HBOS Knowledge Backend Binding',target,'enabled',value,update_modified=False)
    elif kind=='space':
        if target not in {'SPACE_QA_SYNTHETIC','SPACE_SHARED_SYNTHETIC','SPACE_PROD_SYNTHETIC'} or value not in (0,1): frappe.throw('Bad space')
        frappe.db.set_value('HBOS Knowledge Space',target,'enabled',value,update_modified=False)
    elif kind in {'withdrawn','version'}:
        if target not in {'DOC_SYNTHETIC_SHARED','DOC_SYNTHETIC_PROD'}: frappe.throw('Bad document')
        if kind=='withdrawn':
            if value not in (0,1): frappe.throw('Bad withdrawal')
            frappe.db.set_value('HBOS Knowledge Document',target,'withdrawn',value,update_modified=False)
        else:
            if value not in {'VERSION_SYNTHETIC_SHARED_1','VERSION_SYNTHETIC_SHARED_2'}: frappe.throw('Bad version')
            if not frappe.db.exists('HBOS Knowledge Version',value):
                frappe.get_doc({'doctype':'HBOS Knowledge Version','version_id':value,
                    'canonical_document_id':target,'version_json':'{"synthetic":true,"version":2}'}).insert(ignore_permissions=True)
            frappe.db.set_value('HBOS Knowledge Document',target,'current_version',value,update_modified=False)
    else: frappe.throw('Bad operation')
    frappe.db.commit()
    return {'committed':True,'manual_cache_flush':False}

def inventory():
    guard()
    result={}
    for dt in ['HBOS Knowledge Reference','HBOS Knowledge Audit']:
        result[dt]=frappe.db.sql('SELECT publication_state,count(*) n FROM `tab'+dt+'` GROUP BY publication_state',as_dict=True)
    return result
