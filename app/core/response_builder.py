"""

Enhanced API Response Service

Provides standardized, optimized API responses with caching and compression

"""

from typing import Any, Dict, List, Optional, Union

from fastapi import Response, status

from fastapi.responses import JSONResponse

import json

import gzip

import time

from datetime import datetime



from app.core.logging_config import get_logger

from app.models.dto import ApiResponseDTO, PaginatedResponseDTO



logger = get_logger(__name__)





class ResponseService:
    """Enhanced response service with optimization features"""
    
    def __init__(self):
        self.compression_threshold = 1024  # Compress responses larger than 1KB
        self.cache_headers = {
            'static': {'Cache-Control': 'public, max-age=3600'},  # 1 hour
            'dynamic': {'Cache-Control': 'private, max-age=300'},  # 5 minutes
            'no_cache': {'Cache-Control': 'no-cache, no-store, must-revalidate'}
        }
    
    def _should_compress(self, content: str) -> bool:
        """Check if response should be compressed"""
        return len(content.encode('utf-8')) > self.compression_threshold
    
    def _compress_content(self, content: str) -> bytes:
        """Compress response content"""
        return gzip.compress(content.encode('utf-8'))
    
    def _add_performance_headers(self, headers: Dict[str, str], start_time: float) -> Dict[str, str]:
        """Add performance-related headers"""
        processing_time = time.time() - start_time
        headers.update({
            'X-Processing-Time': f"{processing_time:.3f}s",
            'X-Timestamp': datetime.utcnow().isoformat(),
            'X-API-Version': '2.0.0'
        })
        return headers
    
    def success_response(self, 
                        data: Any = None, 
                        message: str = "Success",
                        status_code: int = status.HTTP_200_OK,
                        cache_type: str = 'dynamic',
                        start_time: Optional[float] = None) -> JSONResponse:
        """Create standardized success response"""
        
        response_data = ApiResponseDTO(
            success=True,
            message=message,
            data=data
        )
        
        # Prepare headers
        headers = self.cache_headers.get(cache_type, self.cache_headers['dynamic']).copy()
        
        if start_time:
            headers = self._add_performance_headers(headers, start_time)
        
        # Convert to JSON
        content = response_data.model_dump_json()
        
        # Check if compression is beneficial
        if self._should_compress(content):
            compressed_content = self._compress_content(content)
            headers['Content-Encoding'] = 'gzip'
            headers['Content-Length'] = str(len(compressed_content))
            
            return Response(
                content=compressed_content,
                status_code=status_code,
                headers=headers,
                media_type='application/json'
            )
        
        return JSONResponse(
            content=response_data.model_dump(mode='json'),
            status_code=status_code,
            headers=headers
        )
    
    def paginated_response(self,
                          data: List[Any],
                          total: int,
                          page: int,
                          page_size: int,
                          message: str = "Success",
                          cache_type: str = 'dynamic',
                          start_time: Optional[float] = None) -> JSONResponse:
        """Create standardized paginated response"""
        
        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        response_data = PaginatedResponseDTO(
            success=True,
            message=message,
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
        # Prepare headers
        headers = self.cache_headers.get(cache_type, self.cache_headers['dynamic']).copy()
        
        # Add pagination headers
        headers.update({
            'X-Total-Count': str(total),
            'X-Page': str(page),
            'X-Page-Size': str(page_size),
            'X-Total-Pages': str(total_pages)
        })
        
        if start_time:
            headers = self._add_performance_headers(headers, start_time)
        
        # Convert to JSON
        content = response_data.model_dump_json()
        
        # Check if compression is beneficial
        if self._should_compress(content):
            compressed_content = self._compress_content(content)
            headers['Content-Encoding'] = 'gzip'
            headers['Content-Length'] = str(len(compressed_content))
            
            return Response(
                content=compressed_content,
                status_code=status.HTTP_200_OK,
                headers=headers,
                media_type='application/json'
            )
        
        return JSONResponse(
            content=response_data.model_dump(mode='json'),
            status_code=status.HTTP_200_OK,
            headers=headers
        )
    
    def error_response(self,
                      message: str,
                      status_code: int = status.HTTP_400_BAD_REQUEST,
                      error_code: Optional[str] = None,
                      details: Optional[Dict[str, Any]] = None,
                      start_time: Optional[float] = None) -> JSONResponse:
        """Create standardized error response"""
        
        response_data = {
            'success': False,
            'error': message,
            'error_code': error_code,
            'details': details
        }
        
        # Prepare headers
        headers = self.cache_headers['no_cache'].copy()
        
        if start_time:
            headers = self._add_performance_headers(headers, start_time)
        
        return JSONResponse(
            content=response_data,
            status_code=status_code,
            headers=headers
        )
    
    def created_response(self,
                        data: Any = None,
                        message: str = "Created successfully",
                        resource_id: Optional[str] = None,
                        start_time: Optional[float] = None) -> JSONResponse:
        """Create standardized creation response"""
        
        headers = self.cache_headers['no_cache'].copy()
        
        if resource_id:
            headers['Location'] = f"/{resource_id}"
        
        if start_time:
            headers = self._add_performance_headers(headers, start_time)
        
        response_data = ApiResponseDTO(
            success=True,
            message=message,
            data=data
        )
        
        return JSONResponse(
            content=response_data.model_dump(mode='json'),
            status_code=status.HTTP_201_CREATED,
            headers=headers
        )
    
    def no_content_response(self, start_time: Optional[float] = None) -> Response:
        """Create no content response"""
        
        headers = {}
        if start_time:
            headers = self._add_performance_headers(headers, start_time)
        
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers=headers
        )
    
    def cached_response(self,
                       data: Any,
                       cache_key: str,
                       max_age: int = 300,
                       start_time: Optional[float] = None) -> JSONResponse:
        """Create cached response with ETag"""
        
        # Generate ETag from data
        import hashlib
        content_hash = hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
        etag = f'"{content_hash}"'
        
        headers = {
            'Cache-Control': f'public, max-age={max_age}',
            'ETag': etag,
            'Vary': 'Accept-Encoding'
        }
        
        if start_time:
            headers = self._add_performance_headers(headers, start_time)
        
        response_data = ApiResponseDTO(
            success=True,
            message="Success",
            data=data
        )
        
        return JSONResponse(
            content=response_data.model_dump(mode='json'),
            status_code=status.HTTP_200_OK,
            headers=headers
        )
    
    def stream_response(self,
                       data_generator,
                       content_type: str = 'application/json',
                       start_time: Optional[float] = None) -> Response:
        """Create streaming response for large datasets"""
        
        headers = {
            'Transfer-Encoding': 'chunked',
            'Cache-Control': 'no-cache'
        }
        
        if start_time:
            headers = self._add_performance_headers(headers, start_time)
        
        async def generate():
            yield '{"success": true, "data": ['
            first = True
            async for item in data_generator:
                if not first:
                    yield ','
                yield json.dumps(item, default=str)
                first = False
            yield ']}'
        
        return Response(
            content=generate(),
            media_type=content_type,
            headers=headers
        )
    
    def health_response(self,
                       status_data: Dict[str, Any],
                       is_healthy: bool = True) -> JSONResponse:
        """Create health check response"""
        
        status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Content-Type': 'application/health+json'
        }
        
        response_data = {
            'status': 'pass' if is_healthy else 'fail',
            'version': '2.0.0',
            'serviceId': 'dino-api',
            'description': 'Dino E-Menu API Health Check',
            'checks': status_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return JSONResponse(
            content=response_data,
            status_code=status_code,
            headers=headers
        )

    """Enhanced response service with optimization features"""

   

    def __init__(self):

      self.compression_threshold = 1024 # Compress responses larger than 1KB

      self.cache_headers = {

        'static': {'Cache-Control': 'public, max-age=3600'}, # 1 hour

        'dynamic': {'Cache-Control': 'private, max-age=300'}, # 5 minutes

        'no_cache': {'Cache-Control': 'no-cache, no-store, must-revalidate'}

      }

   

    def _should_compress(self, content: str) -> bool:

      """Check if response should be compressed"""

      return len(content.encode('utf-8')) > self.compression_threshold

   

    def _compress_content(self, content: str) -> bytes:

      """Compress response content"""

      return gzip.compress(content.encode('utf-8'))

   

    def _add_performance_headers(self, headers: Dict[str, str], start_time: float) -> Dict[str, str]:

      """Add performance-related headers"""

      processing_time = time.time() - start_time

      headers.update({

        'X-Processing-Time': f"{processing_time:.3f}s",

        'X-Timestamp': datetime.utcnow().isoformat(),

        'X-API-Version': '2.0.0'

      })

      return headers

    

    def success_response(self, 

              data: Any = None, 

              message: str = "Success",

              status_code: int = status.HTTP_200_OK,

              cache_type: str = 'dynamic',

              start_time: Optional[float] = None) -> JSONResponse:

      """Create standardized success response"""

      

      response_data = ApiResponseDTO(

        success=True,

        message=message,

        data=data

      )

      

      # Prepare headers

      headers = self.cache_headers.get(cache_type, self.cache_headers['dynamic']).copy()

      

      if start_time:

        headers = self._add_performance_headers(headers, start_time)

      

      # Convert to JSON

      content = response_data.model_dump_json()

      

      # Check if compression is beneficial

      if self._should_compress(content):

        compressed_content = self._compress_content(content)

        headers['Content-Encoding'] = 'gzip'

        headers['Content-Length'] = str(len(compressed_content))

        

        return Response(

          content=compressed_content,

          status_code=status_code,

          headers=headers,

          media_type='application/json'

        )

      

      return JSONResponse(

        content=response_data.model_dump(mode='json'),

        status_code=status_code,

        headers=headers

      )

    

    def paginated_response(self,

              data: List[Any],

              total: int,

              page: int,

              page_size: int,

              message: str = "Success",

              cache_type: str = 'dynamic',

              start_time: Optional[float] = None) -> JSONResponse:

      """Create standardized paginated response"""

      

      # Calculate pagination metadata

      total_pages = (total + page_size - 1) // page_size

      has_next = page < total_pages

      has_prev = page > 1

      

      response_data = PaginatedResponseDTO(

        success=True,

        message=message,

        data=data,

        total=total,

        page=page,

        page_size=page_size,

        total_pages=total_pages,

        has_next=has_next,

        has_prev=has_prev

      )

      

      # Prepare headers

      headers = self.cache_headers.get(cache_type, self.cache_headers['dynamic']).copy()

      

      # Add pagination headers

      headers.update({

        'X-Total-Count': str(total),

        'X-Page': str(page),

        'X-Page-Size': str(page_size),

        'X-Total-Pages': str(total_pages)

      })

      

      if start_time:

        headers = self._add_performance_headers(headers, start_time)

      

      # Convert to JSON

      content = response_data.model_dump_json()

      

      # Check if compression is beneficial

      if self._should_compress(content):

        compressed_content = self._compress_content(content)

        headers['Content-Encoding'] = 'gzip'

        headers['Content-Length'] = str(len(compressed_content))

        

        return Response(

          content=compressed_content,

          status_code=status.HTTP_200_OK,

          headers=headers,

          media_type='application/json'

        )

      

      return JSONResponse(

        content=response_data.model_dump(mode='json'),

        status_code=status.HTTP_200_OK,

        headers=headers

      )

    

    def error_response(self,

            message: str,

            status_code: int = status.HTTP_400_BAD_REQUEST,

            error_code: Optional[str] = None,

            details: Optional[Dict[str, Any]] = None,

            start_time: Optional[float] = None) -> JSONResponse:

      """Create standardized error response"""

      

      response_data = {

        'success': False,

        'error': message,

        'error_code': error_code,

        'details': details

      }

      

      # Prepare headers

      headers = self.cache_headers['no_cache'].copy()

      

      if start_time:

        headers = self._add_performance_headers(headers, start_time)

      

      return JSONResponse(

        content=response_data,

        status_code=status_code,

        headers=headers

      )

    

    def created_response(self,

              data: Any = None,

              message: str = "Created successfully",

              resource_id: Optional[str] = None,

              start_time: Optional[float] = None) -> JSONResponse:

      """Create standardized creation response"""

      

      headers = self.cache_headers['no_cache'].copy()

      

      if resource_id:

        headers['Location'] = f"/{resource_id}"

      

      if start_time:

        headers = self._add_performance_headers(headers, start_time)

      

      response_data = ApiResponseDTO(

        success=True,

        message=message,

        data=data

      )

      

      return JSONResponse(

        content=response_data.model_dump(mode='json'),

        status_code=status.HTTP_201_CREATED,

        headers=headers

      )

    

    def no_content_response(self, start_time: Optional[float] = None) -> Response:

      """Create no content response"""

      

      headers = {}

      if start_time:

        headers = self._add_performance_headers(headers, start_time)

      

      return Response(

        status_code=status.HTTP_204_NO_CONTENT,

        headers=headers

      )

    

    def cached_response(self,

              data: Any,

              cache_key: str,

              max_age: int = 300,

              start_time: Optional[float] = None) -> JSONResponse:

      """Create cached response with ETag"""

      

      # Generate ETag from data

      import hashlib

      content_hash = hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

      etag = f'"{content_hash}"'

      

      headers = {

        'Cache-Control': f'public, max-age={max_age}',

        'ETag': etag,

        'Vary': 'Accept-Encoding'

      }

      

      if start_time:

        headers = self._add_performance_headers(headers, start_time)

      

      response_data = ApiResponseDTO(

        success=True,

        message="Success",

        data=data

      )

      

      return JSONResponse(

        content=response_data.model_dump(mode='json'),

        status_code=status.HTTP_200_OK,

        headers=headers

      )

    

    def stream_response(self,

              data_generator,

              content_type: str = 'application/json',

              start_time: Optional[float] = None) -> Response:

      """Create streaming response for large datasets"""

      

      headers = {

        'Transfer-Encoding': 'chunked',

        'Cache-Control': 'no-cache'

      }

      

      if start_time:

        headers = self._add_performance_headers(headers, start_time)

      

      async def generate():

        yield '{"success": true, "data": ['

        first = True

        async for item in data_generator:

          if not first:

            yield ','

          yield json.dumps(item, default=str)

          first = False

        yield ']}'

      

      return Response(

        content=generate(),

        media_type=content_type,

        headers=headers

      )

    

    def health_response(self,

              status_data: Dict[str, Any],

              is_healthy: bool = True) -> JSONResponse:

      """Create health check response"""

      

      status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

      

      headers = {

        'Cache-Control': 'no-cache, no-store, must-revalidate',

        'Content-Type': 'application/health+json'

      }

      

      response_data = {

        'status': 'pass' if is_healthy else 'fail',

        'version': '2.0.0',

        'serviceId': 'dino-api',

        'description': 'Dino E-Menu API Health Check',

        'checks': status_data,

        'timestamp': datetime.utcnow().isoformat()

      }

      

      return JSONResponse(

        content=response_data,

        status_code=status_code,

        headers=headers

      )





# Global response service instance

response_service = ResponseService()





def get_response_service() -> ResponseService:

  """Get response service instance"""

  return response_service





# Convenience functions for common responses

def success(data: Any = None, 

      message: str = "Success",

      cache_type: str = 'dynamic',

      start_time: Optional[float] = None) -> JSONResponse:

  """Create success response"""

  return response_service.success_response(data, message, cache_type=cache_type, start_time=start_time)





def paginated(data: List[Any],

       total: int,

       page: int,

       page_size: int,

       message: str = "Success",

       cache_type: str = 'dynamic',

       start_time: Optional[float] = None) -> JSONResponse:

  """Create paginated response"""

  return response_service.paginated_response(

    data, total, page, page_size, message, cache_type, start_time

  )





def error(message: str,

     status_code: int = status.HTTP_400_BAD_REQUEST,

     error_code: Optional[str] = None,

     details: Optional[Dict[str, Any]] = None,

     start_time: Optional[float] = None) -> JSONResponse:

  """Create error response"""

  return response_service.error_response(message, status_code, error_code, details, start_time)





def created(data: Any = None,

      message: str = "Created successfully",

      resource_id: Optional[str] = None,

      start_time: Optional[float] = None) -> JSONResponse:

  """Create creation response"""

  return response_service.created_response(data, message, resource_id, start_time)