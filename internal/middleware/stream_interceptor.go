package middleware

import (
	"net/http"
	"strings"
)

type JanusHTTPStream struct {
	//  Anonymous Struct Embedding for default methods inheritance
	http.ResponseWriter


}

func (s *JanusHTTPStream) Write(b []byte) (int, error){

	chunk := string(b)

	// placeholder for replacing from cache
	chunk = strings.ReplaceAll(chunk,"EMAIL_1","user@company.com")

	res,err := s.ResponseWriter.Write([]byte(chunk))

	return res,err

}

 func (s *JanusHTTPStream) Flush() {  
        // If the underlying original writer supports flushing, trigger it!    
        if flusher, ok := s.ResponseWriter.(http.Flusher); ok {                     
            flusher.Flush()                
        }                                  
    }                                      
      