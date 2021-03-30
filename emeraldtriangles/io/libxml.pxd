# Based on https://github.com/lxml/lxml/blob/master/src/lxml/includes/xmlparser.pxd

from libc.string cimport const_char

cdef extern from "libxml/parser.h":
    ctypedef unsigned char xmlChar
    ctypedef const xmlChar const_xmlChar "const xmlChar"
    
    ctypedef void (*startElementNsSAX2Func)(void* ctx,
                                            const_xmlChar* localname,
                                            const_xmlChar* prefix,
                                            const_xmlChar* URI,
                                            int nb_namespaces,
                                            const_xmlChar** namespaces,
                                            int nb_attributes,
                                            int nb_defaulted,
                                            const_xmlChar** attributes)

    ctypedef void (*endElementNsSAX2Func)(void* ctx,
                                          const_xmlChar* localname,
                                          const_xmlChar* prefix,
                                          const_xmlChar* URI)

    ctypedef void (*startElementSAXFunc)(void* ctx, const_xmlChar* name, const_xmlChar** atts)

    ctypedef void (*endElementSAXFunc)(void* ctx, const_xmlChar* name)

    ctypedef void (*charactersSAXFunc)(void* ctx, const_xmlChar* ch, int len)

    ctypedef void (*cdataBlockSAXFunc)(void* ctx, const_xmlChar* value, int len)

    ctypedef void (*commentSAXFunc)(void* ctx, const_xmlChar* value)

    ctypedef void (*processingInstructionSAXFunc)(void* ctx, 
                                                  const_xmlChar* target,
                                                  const_xmlChar* data)

    ctypedef void (*internalSubsetSAXFunc)(void* ctx, 
                                            const_xmlChar* name,
                                            const_xmlChar* externalID,
                                            const_xmlChar* systemID)

    ctypedef void (*endDocumentSAXFunc)(void* ctx)

    ctypedef void (*startDocumentSAXFunc)(void* ctx)

    ctypedef void (*referenceSAXFunc)(void * ctx, const_xmlChar* name)

    cdef int XML_SAX2_MAGIC

    ctypedef struct xmlSAXHandler:
        internalSubsetSAXFunc           internalSubset
        startElementNsSAX2Func          startElementNs
        endElementNsSAX2Func            endElementNs
        startElementSAXFunc             startElement
        endElementSAXFunc               endElement
        charactersSAXFunc               characters
        cdataBlockSAXFunc               cdataBlock
        referenceSAXFunc                reference
        commentSAXFunc                  comment
        processingInstructionSAXFunc	processingInstruction
        startDocumentSAXFunc            startDocument
        endDocumentSAXFunc              endDocument

    cdef extern int xmlSAXUserParseFile(xmlSAXHandler *sax, void *user_data, const char *filename)
