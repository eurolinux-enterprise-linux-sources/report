
#include <stdlib.h>
#include <stdio.h>

#include "strata_client.h"

const char baseURL[] = "http://support-services-devel.gss.redhat.com:8080/Strata";

const char dummy_signature[] = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><signature xmlns=\"http://www.redhat.com/gss/strata\"><date>2010-03-08T12:32:11.982+10:00</date><who>someone@somewhere</who><type>kernel</type><signature>U0dWc2JHOGdWMjl5YkdR</signature></signature>";

const char slightly_bad_signature[] = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><report xmlns=\"http://www.redhat.com/gss/strata\"><date>2010-03-08T12:32:11.982+10:00</date><who>someone@somewhere</who><type>kernel</type><signature>U0dWc2JHOGdWMjl5YkdR</signature></signature>";

const char very_bad_signature[] = "this is garbage";


int
main(int argc, char** argv) {

  const char* p;

  printf("\npost_signature(slightly_bad_signature):\n");
  p = post_signature(baseURL, "dummyUser", "dummyPass", slightly_bad_signature);
  if (p) {
    printf("%s\n", p );
    free((void*)p);
  }
  else {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  }

  printf("\npost_signature(very_bad_signature):\n");
  p = post_signature(baseURL, "dummyUser", "dummyPass", very_bad_signature);
  if (p) {
    printf("%s\n", p );
    free((void*)p);
  }
  else {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  }

  printf("\npost_signature(BADURL,dummy_signature):\n");
  p = post_signature("http://support-services-devel.gss.redhat.com:8080/Strata/bad", "dummyUser", "dummyPass", dummy_signature);
  if (p) {
    printf("%s\n", p );
    free((void*)p);
  }
  else {
    fprintf(stderr, "%s\n", strata_client_strerror());
    exit(2);
  }
  
  printf("\npost_signature(VERYBADURL, dummy_signature):\n");
  p = post_signature("http://no.place.like.home/Strata", "dummyUser", "dummyPass", dummy_signature);
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
