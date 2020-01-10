#define _GNU_SOURCE 

#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <unistd.h>
#include <ctype.h>
#include <fcntl.h>
#include <locale.h>
#include <stdint.h>

#include <sys/stat.h>
#include <sys/types.h>

#include <libxml/encoding.h>
#include <libxml/xmlwriter.h>
#include <curl/curl.h>

#include "strata_client.h"

struct reportfile {
  char* tmpdir;
  xmlTextWriterPtr writer;
  xmlBufferPtr buf;
  int issignature;
};

static char* internal_error_string = NULL;

static char*
ssprintf( const char* format, ... ) {
  int r;
  va_list p;
  char* retval;

  va_start(p, format);
  r = vasprintf(&retval, format, p);
  va_end(p);

  if (r < 0) {
    internal_error_string = strdup("ssprintf: vasprintf failed");
    if (!internal_error_string) 
      internal_error_string = "ssprintf: vasprintf failed";
    return 0;
  }

  return retval;
}

static void
internal_error_printf( const char* format, ... ) {
  int r;
  va_list p;

  va_start(p, format);
  r = vasprintf(&internal_error_string, format, p);
  va_end(p);

  if (r < 0) {
    internal_error_string = strdup("internal_error_printf: vasprintf failed");
    if (!internal_error_string) 
      internal_error_string = "internal_error_printf: vasprintf failed";
  } 
}

static int 
run_command( const char *cmd )
{
    int retcode = system(cmd);
    if (retcode) {
      internal_error_printf("'%s' exited with status %d", cmd, retcode);
      return -1;
    }
    return 0;
}

static int
copy_file( const char *src_name, const char *dst_name )
{
  char* cmd = ssprintf("cp %s %s", src_name, dst_name);
  if (!cmd)
    return -1;
  return run_command(cmd);
}

static char*
concat_path_file(const char *path, const char *filename) {
  // This adds concats the two names, adding or removing one slash
  // as necessary.  It does not handle the case that path ends
  // in, or filename starts with, multiple slashs.

  const char* path_end = path + strlen(path) - 1;
  if ((*path_end == '/') != (*filename == '/'))
    // one has it, the other doesn't
    return ssprintf("%s%s", path, filename);
  else if (*filename == '/')
    // they both have it
    return ssprintf("%s%s", path, filename+1);
  else
    // neither has it
    return ssprintf("%s/%s", path, filename);
}



static int
write_rgn_to_file( const char *value, size_t size,
                   const char *path, const char *fname ) {

  char* ofile_name = concat_path_file(path, fname);
  if (!ofile_name)
    return -1;

  FILE *ofile = fopen(ofile_name, "w");
  if (!ofile) {
    internal_error_printf("Can't open '%s'", ofile_name);
    return -1;
  }

  size_t value_size = (size == SIZE_MAX) ? strlen(value) : size;
  if (value_size != fwrite(value, 1, value_size, ofile)) {
    internal_error_printf("Can't write to '%s'", ofile_name);
    return -1;
  }

  fclose(ofile);
  return 0;
}

const char* 
strata_client_strerror( void ) {
  return internal_error_string;
}

//
// The purpose of all the reportfile_XXX functions is to 
// collect up the contents of a report or signature into a 
// single tarball or xml file.
// 


// 
// This allocates a reportfile_t structure and initializes it.
//
//   Set 'issignature' to true if you only want an xml file.
//   If 'issignature' is true, then any bindings which would 
//   be written to an external file are dropped.
//
reportfile_t* 
reportfile_start( int issignature ) {

  // create a new reportfile_t
  reportfile_t* file = (reportfile_t*)malloc(sizeof(reportfile_t));

  file->issignature = issignature;

  // make a temp directory to work in
  file->tmpdir = strdup("/tmp/reportfileXXXXXX");
  if (mkdtemp(file->tmpdir) == NULL) {
    internal_error_printf("Can't mkdir a temporary directory in /tmp");
    return NULL;
  }

  // create a 'content' dir within temp directory
  char* content_dir_name = concat_path_file(file->tmpdir, "content");
  if (!content_dir_name)
    return NULL;
  if (mkdir(content_dir_name, 0700)) {
    internal_error_printf("Can't mkdir '%s'\n", content_dir_name);
    return NULL;
  }

  // set up a libxml 'buffer' and 'writer' to that buffer
  file->buf = xmlBufferCreate();
  if (file->buf == NULL) {
    internal_error_printf("strata_client: Error creating the xml buffer\n");
    return NULL;
  }
  file->writer = xmlNewTextWriterMemory(file->buf, 0);
  if (file->writer == NULL) {
    internal_error_printf("strata_client: Error creating the xml writer\n");
    return NULL;
  }

  // start a new xml document
  int rc;
  rc = xmlTextWriterStartDocument(file->writer, NULL, NULL, NULL);
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterStartDocument\n");
    return NULL;
  }

  // start the document element 'report'
  rc = xmlTextWriterStartElement(file->writer, (const xmlChar*)"report");
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterStartElement\n");
    return NULL;
  }

  // add the 'xmlns' attribue
  rc = xmlTextWriterWriteAttribute(file->writer, (const xmlChar*)"xmlns",
                                   (const xmlChar*)"http://www.redhat.com/gss/strata");
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterWriteAttribute\n");
    return NULL;
  }

  free(content_dir_name);
  return file;
}


static int
internal_reportfile_start_binding( reportfile_t* file, const char* name, 
                                   int isbinary, const char* filename ) {
  int rc;
  
  // open a binding element
  rc = xmlTextWriterStartElement(file->writer, (const xmlChar*)"binding");
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterStartElement\n");
    return -1;
  }

  // add the 'name' attribue
  rc = xmlTextWriterWriteAttribute(file->writer, (const xmlChar*)"name", (const xmlChar*)name);
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterWriteAttribute\n");
    return -1;
  }


  // add the 'filename' attribute if neede
  if (filename) {
    rc = xmlTextWriterWriteAttribute(file->writer, (const xmlChar*)"fileName", (const xmlChar*)filename);
    if (rc < 0) {
      internal_error_printf
	("strata_client: Error at xmlTextWriterWriteAttribute\n");
      return -1;
    }
  }

  // add the 'type' attribute
  if (isbinary) {
    rc = xmlTextWriterWriteAttribute(file->writer, (const xmlChar*)"type", (const xmlChar*)"binary");
    if (rc < 0) {
      internal_error_printf
	("strata_client: Error at xmlTextWriterWriteAttribute\n");
      return -1;
    }
  }
  else {
    rc = xmlTextWriterWriteAttribute(file->writer, (const xmlChar*)"type", (const xmlChar*)"text");
    if (rc < 0) {
      internal_error_printf
	("strata_client: Error at xmlTextWriterWriteAttribute\n");
      return -1;
    }
  }
  return 0;
}

//
// Add a new binding to a report, for a binding whos value is represented
//   as either a null-terminated string or start+len region of memory.
//
//   'file' is the reportfile to add the binding to.
//   'name' is the name of the binding
//   'isbinary' should be true if the data in local_filename is not UTF-8
//       (or compatible, like ASCII).
//   'filename' is the original name of the file this data was obtained from
//   
//   'value' and 'size' hold the value to be bound to 'name'
//      If 'size' == SIZE_MAX then 'value' is treated as a null-terminated
//        string; otherwise 'value' the start of a region of memory 'size' 
//        bytes long.
//
//      Note that while it is valid to set 'isbinary' for a value that is
//        a null-terminated string, it probably is not correct.
//
static int
reportfile_add_binding_from_region( reportfile_t* file, 
                                    const char* name, 
                                    const void* value,
                                    size_t size,
                                    int isbinary, 
                                    const char* filename ) {
  int rc;

  // start the binding element with primary attributes
  rc = internal_reportfile_start_binding(file, name, isbinary, filename);
  if (rc < 0)
    return rc;


  // write the value of the binding, in the way that makes sense
  //   given it's value
  if (isbinary) {
    char* content_dir_name = concat_path_file(file->tmpdir, "content");
    if (!content_dir_name)
      return -1;
    rc = write_rgn_to_file(value, size, content_dir_name, name);
    if (rc < 0)
      return rc;
    free(content_dir_name);

    char* href_name = concat_path_file("content", name);
    if (!href_name)
      return -1;
    rc = xmlTextWriterWriteAttribute(file->writer, 
                                     (const xmlChar*)"href", 
                                     (const xmlChar*)content_dir_name);
    free(href_name);
    if (rc < 0) {
      internal_error_printf
	("strata_client: Error at xmlTextWriterWriteAttribute\n");
      return -1;
    }
  }
  else {
    rc = xmlTextWriterWriteAttribute(file->writer, 
                                     (const xmlChar*)"value", 
                                     (const xmlChar*)value);
      if (rc < 0) {
        internal_error_printf
	  ("strata_client: Error at xmlTextWriterWriteAttribute\n");
        return -1;
    }
  }

  rc = xmlTextWriterEndElement(file->writer);
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterEndElement\n");
    return -1;
  }
  return 0;
}

// Add a new binding to a report, for a binding whos value is represented
//   as a null-terminated string.
//
//   'file' is the reportfile to add the binding to.
//   'name' is the name of the binding
//   'isbinary' should be true if the data in local_filename is not UTF-8
//       (or compatible, like ASCII).
//   'filename' is the original name of the file this data was obtained from
//   'value' is a null-terminated string to bound to name.
//      Note that while it is valid to set 'isbinary' for a value that is
//        a null-terminated string, it probably is not correct.
//
int
reportfile_add_binding_from_string( reportfile_t* file, 
                                    const char* name, 
                                    const char* value,
                                    int isbinary, 
                                    const char* filename ) {
  return reportfile_add_binding_from_region(file, name, 
                                            value, SIZE_MAX, 
                                            isbinary, filename);
}

// Add a new binding to a report, for a binding whos value is represented
//   as a null-terminated string.
//
//   'file' is the reportfile to add the binding to.
//   'name' is the name of the binding
//   'isbinary' should be true if the data in local_filename is not UTF-8
//       (or compatible, like ASCII).
//   'filename' is the original name of the file this data was obtained from
//   'value' is a null-terminated string to bound to name.
//      Note that while it is valid to set 'isbinary' for a value that is
//        a null-terminated string, it probably is not correct.
//
int
reportfile_add_binding_from_memory( reportfile_t* file, 
                                    const char* name, 
                                    const void* value,
                                    size_t size,
                                    int isbinary, 
                                    const char* filename ) {
  if (size == SIZE_MAX)
    {
      internal_error_printf(
          "reportfile_add_binding_from_memory: error 'size' too long");
      return -1;
    }
  return reportfile_add_binding_from_region(file, name, 
                                            value, size, 
                                            isbinary, filename);
}



//
// Add a new binding to a report, for a binding whos value is represented
//   as a named file.
//
//   'file' is the reportfile to add the binding to.
//   'name' is the name of the binding
//   'isbinary' should be true if the data in local_filename is not UTF-8
//       (or compatible, like ASCII).
//   'filename' is the original name of the file this data was obtained from
//   
//   'local_filename' is the name of the file containing the bindings value
//      'filename' and 'local_filename' can be the same, but don't need to
//         be the same.
//
int
reportfile_add_binding_from_namedfile( reportfile_t* file, const char* name, const char* local_filename, int isbinary, const char* filename ) {
  int rc;

  rc = internal_reportfile_start_binding(file, name, isbinary, filename);
  if (rc < 0)
    return rc;

  char* content_dir_name = concat_path_file(file->tmpdir, "content");
  if (!content_dir_name)
    return -1;
  char* ofile_name = concat_path_file(content_dir_name, name);
  if (!ofile_name)
    return -1;
  rc = copy_file(local_filename, ofile_name);
  if (rc < 0)
    return rc;
  free(content_dir_name);
  free(ofile_name);

  
  char* href_name = concat_path_file("content", name);
  if (!href_name)
    return -1;
  rc = xmlTextWriterWriteAttribute(file->writer, (const xmlChar*)"href", (const xmlChar*)href_name);
  if (rc < 0) {
    internal_error_printf
	("strata_client: Error at xmlTextWriterWriteAttribute\n");
      return -1;
    }

  free(href_name);
  return 0;
}

//
// End the reportfile, and prepare it for delivery. 
// No more bindings can be added after this.
//
int
reportfile_end( reportfile_t* file ) {

  int rc;

  // close off the end of the xml file
  rc = xmlTextWriterEndDocument(file->writer);
  if (rc < 0) {
    internal_error_printf("strata_client: Error at xmlTextWriterEndDocument\n");
    return -1;
  }

  xmlFreeTextWriter(file->writer);
  file->writer = NULL;

  return 0;
}

//
// Write the reportfile to 'outfile_name'
//
// Currently this only works if the reportfile is a Report.
//
int
reportfile_write_to_file( reportfile_t* file, const char* outfile_name ) {

  if (0) {
    internal_error_printf("error: reportfile_write_to_file called before reportfile_end");
    return -1;
  }

  if (file->issignature) {
    internal_error_printf("error: reportfile_write_to_file called on signature");
    return -1;
  }



  int rc;
  // write the contents of the xmlfile to 'content.xml'
  rc = write_rgn_to_file((const char*)file->buf->content, SIZE_MAX, 
                         file->tmpdir, "content.xml");
  if (rc < 0)
    return rc;

  // tar up the contents
  char* cmd = ssprintf("tar --file=%s -C %s --create --gzip content content.xml", outfile_name, file->tmpdir);
  if (!cmd) 
    return -1;
  rc = run_command(cmd);
  if (rc < 0)
    return -1;
  free(cmd);

  return 0;
}


//
// Return the contents of the reportfile as a string.
//
// Currently only works if 'file' is a signature.
//
char* 
reportfile_as_string( reportfile_t* file ) {

  if (0) {
    internal_error_printf("error: reportfile_as_string called before reportfile_end");
    return NULL;
  }

  if (!file->issignature) {
    internal_error_printf("error: reportfile_as_string called on non-signature");
    return NULL;
  }

  return strdup((const char*)file->buf->content);
}



//
// free the reportfile
//
int
reportfile_free( reportfile_t* file ) {
  
  if (file) {
    int rc;
    char* cmd;

    // delete the temp dir
    cmd = ssprintf("rm -rf %s", file->tmpdir);
    if (!cmd) 
      return -1;
    rc = run_command(cmd);
    if (rc < 0)
      return -1;
    free(cmd);

    xmlFreeTextWriter(file->writer);
    xmlBufferFree(file->buf);
    free(file->tmpdir);
    free(file);
  }

  return 0;
}




static void
internal_error_curl(CURLcode err, const char* msg1, const char* msg2)
{
  internal_error_printf("error: %s: %s: %s", msg1, msg2, curl_easy_strerror(err));
}


typedef struct response_data {
  long code;
  const char* location;
  const char* strata_message;
  const char* http_header;
  char* body;
  size_t body_size;
} response_data_t;

static void 
response_data_free(const response_data_t* response_data) {
  free((void*)response_data->http_header);
  free((void*)response_data->strata_message);
  free((void*)response_data->body);
  free((void*)response_data->location);
  free((void *)response_data);
}  


// 
// Examine each header looking for "Location:" or "Strata-Message:" headers
// 
static size_t 
headerfunction(void *buffer_pv, size_t count, size_t nmemb, void *response_data_pv)
{
  size_t size = count * nmemb;
  struct response_data* response_data = (struct response_data*)response_data_pv;
  const char* buffer = (const char*)buffer_pv;

  const char location_key[] = "Location:";
  const size_t location_key_size = sizeof(location_key)-1;

  if (size >= location_key_size
      && 0 == memcmp(buffer,location_key,location_key_size)) {
    const char* start = (const char*) buffer+location_key_size+1;
    const char* end;

    // skip over any leading space
    while (start < buffer+size 
           && isspace(*start)) ++start;

    end = start;

    // skip till we find the end of the url (first space or end of buffer)
    while (end < buffer+size 
           && !isspace(*end)) ++end;

    response_data->location = strndup(start,end-start);
  }


  const char strata_message_key[] = "Strata-Message:";
  const size_t strata_message_key_size = sizeof(strata_message_key)-1;

  if (size >= strata_message_key_size
      && 0 == memcmp(buffer,strata_message_key,strata_message_key_size)) {
    const char* tmp_msg = (const char*) buffer+strata_message_key_size;
    const char* tmp_end = (const char*) buffer+size-2;  // trim trailing \r\n

    while (tmp_msg < tmp_end && isspace(*tmp_msg)) 
      tmp_msg++;

    while (tmp_msg < tmp_end && isspace(*(tmp_end-1)))
      tmp_end--;

    size_t tmp_msg_len = tmp_end - tmp_msg;

    if (response_data->strata_message) {
      const char* old_msg = response_data->strata_message;
      const size_t old_msg_len = strlen(old_msg);
      const size_t new_msg_len = old_msg_len + tmp_msg_len + 1;
      char* new_msg = (char*)malloc(new_msg_len+1);

      mempcpy(mempcpy(mempcpy(new_msg, old_msg, old_msg_len), 
                              " ", 1), 
                              tmp_msg, tmp_msg_len);
      new_msg[new_msg_len] = 0;
      response_data->strata_message = new_msg;
      free((void*)old_msg);
    } else {
      response_data->strata_message = strndup(tmp_msg, tmp_msg_len);
    }
  }

  const char http_header_key[] = "HTTP/";
  const size_t http_header_key_size = sizeof(http_header_key)-1;

  if (size >= http_header_key_size
      && 0 == memcmp(buffer,http_header_key,http_header_key_size)) {
    const char* tmp_msg = (const char*) buffer;
    const char* tmp_end = (const char*) buffer+size-2;  // trim trailing \r\n
    size_t tmp_msg_len = tmp_end - tmp_msg;

    response_data->http_header = strndup(tmp_msg, tmp_msg_len);
  }

  return size;
}

static int
append_accept_language_header(struct curl_slist ** httpheader_list_ptr) {

  // get the current MESSAGES locale
  char* environ_locale = setlocale(LC_MESSAGES, NULL);


  // catch all the locales we don't care about
  if (environ_locale == NULL 
      || 0 == strcmp("", environ_locale)
      || 0 == strcmp("C", environ_locale)
      || 0 == strcmp("POSIX", environ_locale))
    return 0;


  // Translate the environ locale to an http locale
  //   strip off everything after the initial list of alpha-numeric-underscores
  //   change underscores to dashes
  char* message_locale = strdup(environ_locale);
  if (!message_locale) {
    internal_error_printf("strdup failed");
    return -1;
  }
  char* p = NULL;
  for (p = message_locale; *p != 0 && (*p == '_' || isalnum(*p)); p++) {
    if (*p == '_')
      *p = '-';
  }
  *p = 0;


  // append the header to the header list
  char* header = ssprintf("Accept-Language: %s", message_locale);
  if (!header)
    return -1;
  *httpheader_list_ptr = curl_slist_append(*httpheader_list_ptr, header);


  free(header);
  free(message_locale);
  return 0;
}
  

  
    
//
// URL: to post to
//
// content_type: of the data
// data: depends on data_size
//   if data_size is 0 or more
//      data is binary data to be sent in post
//   if data_size == -1 
//      data is NULL terminated string to be sent in post
//   if data_size == -2 
//      data is name of file whose contents are to be sent in post
//   if data_size == -3 
//      data is name of file whose contents are to be sent in post
//      the file is sent as a multipart/form-data post
//


static response_data_t* 
post(const char* URL, 
     const char* username,
     const char* password,
     const char* content_type,
     const char* data,
     const long data_size) {

  CURLcode rc;
  CURL *handle = curl_easy_init();
  //  FILE* file;
  response_data_t* response_data = (response_data_t*)calloc(1,sizeof(response_data_t));

  rc = curl_easy_setopt(handle, CURLOPT_VERBOSE, 0);
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_VERBOSE)");
    return NULL;
  }
  rc = curl_easy_setopt(handle, CURLOPT_NOPROGRESS, 1);
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_NOPROGRESS)");
    return NULL;
  }


  rc = curl_easy_setopt(handle, CURLOPT_POST, 1);
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_POST)");
    return NULL;
  }

  rc = curl_easy_setopt(handle, CURLOPT_URL, URL);
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_URL)");
    return NULL;
  }

  if (username) {
    rc = curl_easy_setopt(handle, CURLOPT_HTTPAUTH, CURLAUTH_BASIC);
    if (rc) {
      internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_HTTPAUTH, CURLAUTH_BASIC)");
      return NULL;
    }

#if defined(CURLOPT_USERNAME) && defined(CURLOPT_PASSWORD)
    rc = curl_easy_setopt(handle, CURLOPT_USERNAME, username);
    if (rc) {
      internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_USERNAME)");
      return NULL;
    }
    
    rc = curl_easy_setopt(handle, CURLOPT_PASSWORD, (password ? password : ""));
    if (rc) {
      internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_PASSWORD)");
      return NULL;
    }
#else
    {
      const char* userpwd = ssprintf("%s:%s", username, 
                                     (password ? password : ""));
      rc = curl_easy_setopt(handle, CURLOPT_USERPWD, userpwd);
      if (rc) {
        internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_USERPWD)");
        return NULL;
      }
      free((void*)userpwd);
    }
#endif
  }
  
  FILE* data_file = 0;
  struct curl_httppost* post = NULL;  
  struct curl_httppost* last = NULL;  

  if (data_size == -2) {
    data_file = fopen(data, "r");
    if (!data_file) {
      internal_error_printf("Can't open file '%s'", data);
      return NULL;
    }
    rc = curl_easy_setopt(handle, CURLOPT_READDATA, data_file);
    if (rc) {
      internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_READDATA)");
      return NULL;
    }

  } else if (data_size == -3) {
    rc = curl_formadd(&post, &last, 
                      CURLFORM_PTRNAME, "file", 
                      CURLFORM_FILE, data, 
                      CURLFORM_CONTENTTYPE, content_type,
                      CURLFORM_FILENAME, data,
                      CURLFORM_END);
    if (rc) {
      internal_error_curl(rc, "problem", "curl_formadd(CURLFORM_FILE)");
      return NULL;
    }
    
    rc = curl_easy_setopt(handle, CURLOPT_HTTPPOST, post);
    if (rc) {
      internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_HTTPPOST);");
      return NULL;
    }

  } else {
    rc = curl_easy_setopt(handle, CURLOPT_POSTFIELDS, data);
    if (rc) {
      internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_POSTFIELDS)");
      return NULL;
    }
    rc = curl_easy_setopt(handle, CURLOPT_POSTFIELDSIZE, data_size);
    if (rc) {
      internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_POSTFIELDSIZE)");
      return NULL;
    }
  }


  struct curl_slist *httpheader_list = NULL;

  if (data_size != -3) {
    char* content_type_header = ssprintf("Content-Type: %s", content_type);
    if (!content_type_header) return NULL;
    httpheader_list = curl_slist_append(httpheader_list,content_type_header);
    free(content_type_header);
  }

  rc = append_accept_language_header(&httpheader_list);
  if (rc) return NULL;

  curl_easy_setopt(handle, CURLOPT_HTTPHEADER, httpheader_list);


  rc = curl_easy_setopt(handle, CURLOPT_HEADERFUNCTION, headerfunction);
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_HEADERFUNCTION)");
    return NULL;
  }

  rc = curl_easy_setopt(handle, CURLOPT_WRITEHEADER, response_data );
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_WRITEHEADER)");
    return NULL;
  }

  FILE* body_stream = open_memstream(&response_data->body, &response_data->body_size); 
  rc = curl_easy_setopt(handle, CURLOPT_WRITEDATA, body_stream);
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_setopt(CURLOPT_WRITEDATA)");
    return NULL;
  }

  rc = curl_easy_perform(handle);
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_perform");
    return NULL;
  }

  rc = curl_easy_getinfo(handle, CURLINFO_RESPONSE_CODE, &response_data->code); 
  if (rc) {
    internal_error_curl(rc, "problem", "curl_easy_getinfo(CURLINFO_RESPONSE_CODE)");
    return NULL;
  }
 
  fclose(body_stream);
  if (data_file) fclose(data_file);
  if (post) curl_formfree(post);
  curl_easy_cleanup(handle);
  curl_slist_free_all(httpheader_list);

  return response_data;
}

static response_data_t* 
post_string(const char* URL,
            const char* username,
            const char* password,
            const char* content_type,
            const char* str) {
  return post(URL, username, password, content_type, str, -1);
}

static response_data_t* 
post_memory(const char* URL,
            const char* username,
            const char* password,
            const char* content_type,
            const char* data,
            const long data_size)
  __attribute__ ((unused));
static response_data_t* 
post_memory(const char* URL,
            const char* username,
            const char* password,
            const char* content_type,
            const char* data,
            const long data_size) {
  if (data_size < 0) {
    internal_error_printf("data size is negative");
    return NULL;
  }

  return post(URL, username, password, content_type, data, data_size);
}

static response_data_t* 
post_namedfile(const char* URL,
               const char* username,
               const char* password,
               const char* content_type,
               const char* namedfile)
  __attribute__ ((unused));
static response_data_t* 
post_namedfile(const char* URL,
               const char* username,
               const char* password,
               const char* content_type,
               const char* namedfile) {
  return post(URL, username, password, content_type, namedfile, -2);
}

static response_data_t* 
postform_namedfile(const char* URL,
                   const char* username,
                   const char* password,
                   const char* content_type,
                   const char* namedfile) {
  return post(URL, username, password, content_type, namedfile, -3);
}











static const char* 
make_case_data(const char* summary, const char* description,
               const char* product, const char* version,
               const char* component) {
  const char* retval;
  xmlTextWriterPtr writer;
  xmlBufferPtr buf;
  int rc;

  buf = xmlBufferCreate();
  if (buf == NULL) {
    internal_error_printf("strata_client: Error creating the xml buffer\n");
    return NULL;
  }
  writer = xmlNewTextWriterMemory(buf, 0);
  if (writer == NULL) {
    internal_error_printf("strata_client: Error creating the xml writer\n");
    return NULL;
  }

  // start a new xml document
  rc = xmlTextWriterStartDocument(writer, NULL, "UTF-8", "yes");
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterStartDocument\n");
    return NULL;
  }

  // start the document element 'case'
  rc = xmlTextWriterStartElement(writer, (const xmlChar*)"case");
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterStartElement\n");
    return NULL;
  }

  // add the 'xmlns' attribue
  rc = xmlTextWriterWriteAttribute(writer, (const xmlChar*)"xmlns",
                                   (const xmlChar*)"http://www.redhat.com/gss/strata");
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterWriteAttribute\n");
    return NULL;
  }

  // open a binding element
  rc = xmlTextWriterWriteElement(writer, (const xmlChar*)"summary", (const xmlChar*)summary);
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterWriteElement\n");
    return NULL;
  }

  rc = xmlTextWriterWriteElement(writer, (const xmlChar*)"description", (const xmlChar*)description);
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterWriteElement\n");
    return NULL;
  }

  if (product) {
    rc = xmlTextWriterWriteElement(writer, (const xmlChar*)"product", (const xmlChar*)product);
    if (rc < 0) {
      internal_error_printf
        ("strata_client: Error at xmlTextWriterWriteElement\n");
      return NULL;
    }
  }

  if (version) {
    rc = xmlTextWriterWriteElement(writer, (const xmlChar*)"version", (const xmlChar*)version);
    if (rc < 0) {
      internal_error_printf
        ("strata_client: Error at xmlTextWriterWriteElement\n");
      return NULL;
    }
  }

  if (component) {
    rc = xmlTextWriterWriteElement(writer, (const xmlChar*)"component", (const xmlChar*)component);
    if (rc < 0) {
      internal_error_printf
        ("strata_client: Error at xmlTextWriterWriteElement\n");
      return NULL;
    }
  }

  // close off the end of the xml file
  rc = xmlTextWriterEndDocument(writer);
  if (rc < 0) {
    internal_error_printf("strata_client: Error at xmlTextWriterEndDocument\n");
    return NULL;
  }

  retval = strdup((const char*)buf->content);
  if (!retval) return NULL;
  xmlFreeTextWriter(writer);
  xmlBufferFree(buf);

  return retval;
}

static const char* 
make_response_xml(const char* title, const char* body, 
                  const char* actualURL, const char* displayURL) {
  const char* retval;
  xmlTextWriterPtr writer;
  xmlBufferPtr buf;
  int rc;
 
  buf = xmlBufferCreate();
  if (buf == NULL) {
    internal_error_printf("strata_client: Error creating the xml buffer\n");
    return NULL;
  }
  writer = xmlNewTextWriterMemory(buf, 0);
  if (writer == NULL) {
    internal_error_printf("strata_client: Error creating the xml writer\n");
    return NULL;
  }
  
  // start a new xml document
  rc = xmlTextWriterStartDocument(writer, NULL, "UTF-8", "yes");
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterStartDocument\n");
    return NULL;
  }

  rc = xmlTextWriterStartElement(writer, (const xmlChar*)"response");
  if (rc < 0) {
    internal_error_printf
      ("strata_client: Error at xmlTextWriterStartElement\n");
    return NULL;
  }

  if (title) {
    rc = xmlTextWriterWriteElement(writer, (const xmlChar*)"title", (const xmlChar*)title);
    if (rc < 0) {
      internal_error_printf
        ("strata_client: Error at xmlTextWriterWriteElement\n");
      return NULL;
    }
  }

  if (body) {
    rc = xmlTextWriterWriteElement(writer, (const xmlChar*)"body", (const xmlChar*)body);
    if (rc < 0) {
      internal_error_printf
        ("strata_client: Error at xmlTextWriterWriteElement\n");
      return NULL;
    }
  }
    
  if (actualURL || displayURL) {
    rc = xmlTextWriterStartElement(writer, (const xmlChar*)"URL");
    if (rc < 0) {
      internal_error_printf
        ("strata_client: Error at xmlTextWriterStartElement\n");
      return NULL;
    }

    if (actualURL) {
      rc = xmlTextWriterWriteAttribute(writer, (const xmlChar*)"href", (const xmlChar*)actualURL);
      if (rc < 0) {
        internal_error_printf
          ("strata_client: Error at xmlTextWriterWriteAttribute\n");
        return NULL;
      }
    }

    if (displayURL) {
      rc = xmlTextWriterWriteString(writer, (const xmlChar*)displayURL);
      if (rc < 0) {
        internal_error_printf
          ("strata_client: Error at xmlTextWriterWriteAttribute\n");
        return NULL;
      }
    }
  }
  
  // close off the end of the xml file
  rc = xmlTextWriterEndDocument(writer);
  if (rc < 0) {
    internal_error_printf("strata_client: Error at xmlTextWriterEndDocument\n");
    return NULL;
  }

  retval = strdup((const char*)buf->content);
  if (!retval) return NULL;
  xmlFreeTextWriter(writer);
  xmlBufferFree(buf);
  
  return retval;
}

static const char*
append_http_response_message(const char* body, 
                             response_data_t* response_data) {

  const char* status = response_data->http_header;
  const char* generated_status = NULL;
  if (!status) {
    generated_status = ssprintf("HTTP Response code %ld", response_data->code);
    if (!generated_status) return NULL;
    status = generated_status;
  }

  if (response_data->code == 200 || response_data->code == 201) {
    /* valid and expected codes, don't add any message to 'body' */
  }

  else if (200 <= response_data->code && response_data->code < 300) {
    const char* new_body = ssprintf("%s%s"
        "%s\n"
        "Server returned a successful response code other than "
            "those expect by this client",
                                    body,
                                    (*body ? "\n" : ""), 
                                    status);
    if (!new_body) return NULL;
    if (new_body != body) {
      free((char*)body);
      body = new_body;
    }
  }
  
  else if (300 <= response_data->code && response_data->code < 400) {
    const char* location = response_data->location;
    if (!location
        || strlen(location) == 0)
      location = "<No location header given.>";
    const char* new_body = ssprintf("%s%s"
        "Unhandled Redirect\n"
        "%s\n"
        "Server returned a redirect response code that this "
            "client does not automatically handle\n"
        "The server is redirecting this request to:\n"
        "    %s\n"
        "If you wish you may change your strata plugin configuration "
            "to point to this URL",
                                    body,
                                    (*body ? "\n" : ""), 
                                    status,
                                    location);
    if (!new_body) return NULL;
    if (new_body != body) {
      free((char*)body);
      body = new_body;
    }
  }
  
  else if (400 <= response_data->code && response_data->code < 500) {
    const char* new_body = ssprintf("%s%s"
                                    "%s",
                                    body,
                                    (*body ? "\n" : ""), 
                                    status);
    if (!new_body) return NULL;
    if (new_body != body) {
      free((char*)body);
      body = new_body;
    }
  }
  
  else if (500 <= response_data->code && response_data->code < 600) {
    const char* new_body = ssprintf("%s%s"
                                    "Server Internal Error\n"
                                    "%s",
                                    body,
                                    (*body ? "\n" : ""), 
                                    status);
    if (!new_body) return NULL;
    if (new_body != body) {
      free((char*)body);
      body = new_body;
    }
  }
  
  else {
    const char* new_body = ssprintf("%s%s"
            "Unexpected Response Code\n"
            "%s\n"
            "Server returned a response code that this client does not handle",
                                    body,
                                    (*body ? "\n" : ""), 
                                    status);
    if (!new_body) return NULL;
    if (new_body != body) {
      free((char*)body);
      body = new_body;
    }
  }

  free((void*)generated_status);
  return body;
}

static const char*
append_response_header(const char* body, const char* action) {
  const char* new_body = ssprintf("%s%sResponse for %s:",
                                  body,
                                  (*body ? "\n" : ""), 
                                  action);
  if (!new_body) return NULL;
  if (new_body != body) {
    free((char*)body);
    body = new_body;
  }
  return body;
}


static const char*
append_response_message(const char* body, 
                        const char* action, 
                        response_data_t* response_data) {
  int header_added = 0;  
 
  if (! (response_data->code == 200 
         || response_data->code == 201)) {
    if (!header_added) {
      body = append_response_header(body, action);
      if (!body) return NULL;
      header_added = 1;
    }
    body = append_http_response_message(body, response_data);
    if (!body) return NULL;
    
    if (response_data->strata_message) {
      const char* new_body = ssprintf("%s%sStrata Server Message: %s",
                                      body,
                                      (*body ? "\n" : ""), 
                                      response_data->strata_message);
      if (!new_body) return NULL;
      if (new_body != body) {
        free((char*)body);
        body = new_body;
      }
    }
  }
  
  if (response_data->body 
      && strlen(response_data->body)) {
    if (!header_added) {
      body = append_response_header(body, action);
      if (!body) return NULL;
      header_added = 1;
    }

    const char* new_body = ssprintf("%s%s%s",
                                    body,
                                    (*body ? "\n" : ""), 
                                    response_data->body);
    if (!new_body) return NULL;
    if (new_body != body) {
      free((char*)body);
      body = new_body;
    }
  }

  return body;
}
  
static const char* 
make_response(const char* action1,
              const char* action2,
              response_data_t* first_response,
              response_data_t* second_response,
              const char* display_url) {
  const char* retval;
  const char* body;
  const char* title;

  if (200 <= first_response->code
      && first_response->code < 300)
    title = ssprintf("%s Succeeded", action1);
  else 
    title = ssprintf("%s Failed", action1);

  if (!title) return NULL;

  body = strdup("");

  body = append_response_message(body, action1, first_response);
  if (!body) return NULL;
  
  if (second_response) {
    const char* new_title;

    if (200 <= second_response->code
        && second_response->code < 300)
      new_title = ssprintf("%s; %s Succeeded", title, action2);
    else 
      new_title = ssprintf("%s; %s Failed", title, action2);

    if (!new_title) return NULL;
    if (new_title != title) {
      free((char*)title);
      title = new_title;
    }

    body = append_response_message(body, action2, second_response);
    if (!body) return NULL;
  }

  retval = make_response_xml(title, body,
                             first_response->location,
                             (first_response->location ?
                              display_url : NULL));
  if (!retval) return NULL;

  free((char*)body);
  free((char*)title);
  return retval;
}

static response_data_t* 
attach_file_to_case( const char* baseURL,
                     const char* username,
                     const char* password,
                     const char* case_name,
                     const char* report_file_name ) {

  const char* attachURL;

  // if case_name is NULL, treat baseURL as caseURL
  if (case_name) {
    const char* freethis;
    const char* caseURL = concat_path_file(baseURL, "/cases");
    if (!caseURL) return NULL;

    freethis = caseURL;
    caseURL = concat_path_file(caseURL, case_name);
    if (!caseURL) return NULL;
    free((void*)freethis);

    attachURL = concat_path_file(caseURL, "/attachments");
    if (!attachURL) return NULL;

    free((void*)caseURL);
  } else {
    attachURL = concat_path_file(baseURL, "/attachments");
    if (!attachURL) return NULL;
  }
  
  int redirect_attach_count = 0;
 redirect_attach:;
  response_data_t* attach_response = 
    postform_namedfile(attachURL, 
                       username, password,
                       "application/binary", 
                       report_file_name);
  if (!attach_response) return NULL;
  
  if (attach_response->code == 305) {
    if ( ++redirect_attach_count > 10 ) {
      internal_error_printf("servers required more than 10 redirects");
      return NULL;
    }

    free((void*)attachURL);
    attachURL = attach_response->location;
    attach_response->location = NULL;
    response_data_free(attach_response);
    goto redirect_attach;
  }
    
  free((void*)attachURL);
  return attach_response;
}

const char* 
post_signature(const char* baseURL, 
               const char* username,
               const char* password,
               const char* signature) {
  const char* URL = concat_path_file(baseURL, "/signatures");

  int redirect_signature_count = 0;
 redirect_signature:;
  response_data_t* response_data = post_string(URL,
                                               username,
                                               password,
                                               "application/xml",
                                               signature);
  if (!response_data)
    return NULL;

  const char* retval;
  switch (response_data->code) {
  case 200:
  case 201:
    if (response_data->body && strlen(response_data->body) > 0) {
      retval = response_data->body;
      response_data->body = NULL;
    }
    else if (response_data->strata_message 
             && strcmp(response_data->strata_message,"CREATED") != 0) {
      retval = response_data->strata_message;
      response_data->strata_message = NULL;
    }
    else {
      retval = strdup("Thank you for submitting your signature.");
      if (!retval) return NULL;
    }
    break;

  case 305: {
    if ( ++redirect_signature_count > 10 ) {
      internal_error_printf("servers required more than 10 redirects");
      return NULL;
    }
    free((void*)URL);
    URL = response_data->location;
    response_data->location = NULL;
    response_data_free(response_data);
    goto redirect_signature;
  }

  default:
    retval = make_response("Signature Submission", "",
                           response_data, NULL,
                           "New Signature");
    if (!retval) return NULL;
  }

  response_data_free(response_data);
  free((void *)URL);
  return retval;
}

response_data_t* 
create_case(const char* baseURL,
            const char* username,
            const char* password,
            const char* case_data_type,
            const char* case_data) {

  const char* URL = concat_path_file(baseURL, "/cases");
  if (!URL) return NULL;

  int redirect_createcase_count = 0;
 redirect_createcase:;
  response_data_t* createcase_response = post_string(URL,
                                                     username,
                                                     password,
                                                     case_data_type,
                                                     case_data);
  if (!createcase_response) return NULL;

  if (createcase_response->code == 305) {
    if ( ++redirect_createcase_count > 10 ) {
      internal_error_printf("servers required more than 10 redirects");
      return NULL;
    }
    free((void*)URL);
    URL = createcase_response->location;
    createcase_response->location = NULL;
    response_data_free(createcase_response);
    goto redirect_createcase;
  }

  free((void*)URL);
  return createcase_response;
}

    

const char* 
send_report_to_new_case( const char* baseURL,
                         const char* username,
                         const char* password,
                         const char* summary,
                         const char* description,
                         const char* component,
                         const char* product,
                         const char* version,
                         const char* report_file_name ) {

  const char* case_data = make_case_data(summary, description,
                                         product, version,
                                         component);
  if (!case_data) return NULL;

  response_data_t* createcase_response = create_case(baseURL,
                                                     username,
                                                     password,
                                                     "application/xml",
                                                     case_data);

  if (!createcase_response) return NULL;

  const char* retval = NULL;
  if (200 <= createcase_response->code
      && createcase_response->code < 300) {

    if (createcase_response->location
        && strlen(createcase_response->location) > 0) {
      response_data_t* attach_response = 
        attach_file_to_case(createcase_response->location, 
                            username, password,
                            NULL,
                            report_file_name);
      if (!attach_response) return NULL;
      retval = make_response("Case Creation", "File Attachment",
                             createcase_response, attach_response,
                             "New Case");
      if (!retval) return NULL;
      response_data_free(attach_response);
    } else {
      /* Case Creation returned valid code, but no location */
      retval = ssprintf("Error: case creation return HTTP Code %ld, "
                        "but no Location URL header", 
                        createcase_response->code);
      if (!retval) return NULL;
    }
  } else {
    retval = make_response("Case Creation", NULL,
                           createcase_response, NULL,
                           "New Case");
    if (!retval) return NULL;
  }

  free((void*)case_data);
  response_data_free(createcase_response);
  return retval;
}

const char* 
send_report_to_existing_case( const char* baseURL,
                              const char* username,
                              const char* password,
                              const char* case_name,
                              const char* report_file_name ) {

  response_data_t* attach_response = 
    attach_file_to_case(baseURL, 
                        username, password, 
                        case_name, report_file_name);

  if (!attach_response) return NULL;
  
  const char* retval = make_response("File Attachment", NULL,
                                     attach_response, NULL,
                                     "New Attachment");
  if (!retval) return NULL;

  response_data_free(attach_response);
  return retval;
}
