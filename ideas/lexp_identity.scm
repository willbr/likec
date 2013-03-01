(define (identity x)
  x)

(define (max a b)
  (if (> a b)
    a
    b))

(define (max a b)
  (if (> a b)
    (identity a)
    (identity b)))

;;;;;;;;;;;;;;;;;;;;;;;;;

lexp

define (max a b)
  if (> a b)
     identity a
     identity b


define (max a b)
  if (> a b)
     $a
     $b

=>

(define (max a b)
  (if (> a b)
     (a)
     (b)))

