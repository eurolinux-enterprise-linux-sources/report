
#include <stdlib.h>
#include <stdio.h>

#include "strata_client.h"

const char baseURL[] = "http://support-services-devel.gss.redhat.com:8080/Strata";


int
main(int argc, char** argv) {
  reportfile_t* file = reportfile_start(1);
  if (!file) {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  }

  int rc;
  char content[] = "this is a test";
  char content_name[] = "testString";
  rc = reportfile_add_binding_from_string(file, content_name, content, 0, 0);
  if (rc < 0) {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  }
    
  rc = reportfile_add_binding_from_namedfile(file, "testFile", "/etc/hosts", 0, "/etc/hosts");
  if (rc < 0) {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  } 
  
  rc = reportfile_end(file);
  if (rc < 0) {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  } 

  char* signature = reportfile_as_string( file );
  if (!signature) {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  } 
  
  rc = reportfile_free( file );
  if (rc < 0) {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  } 

  const char* p;

  printf("\npost_signature(signature):\n");
  p = post_signature(baseURL, "dummyUser", "dummyPassword", signature);
  if (p) {
    printf("%s\n", p );
    free((void*)signature);
    free((void*)p);
  }
  else {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  }

  printf("\ncreate_case(dummy_summary, dummy_description, sealert-report.xml):\n");
  p = send_report_to_new_case(baseURL, "dummyUser", "dummyPassword", "c_strata_client_created test case summary", "c_strata_client_created test case description", "c_strata_client_created test case component", "Red Hat Enterprise Linux", "6.0", "sealert-report.xml");
  if (p) {
    printf("%s\n", p );
    free((void*)p);
  }
  else {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  }

  return 0;
}
