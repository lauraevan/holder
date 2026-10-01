  (func (;12725;) (type 40150) (param (ref null 22600))
    (local (ref null 11) (ref null 11) (ref null 12) i32 (ref null 10) (ref null 11) (ref null 11) (ref null 21245) i32 (ref null 24385) funcref)
    call 111
    local.set 10
    local.get 10
    call 112
    if ;; label = @1
      local.get 10
      call 108
      local.set 9
      local.get 10
      call 102
      ref.cast (ref null 21245)
      local.set 8
      local.get 10
      call 102
      ref.cast (ref null 11)
      local.set 7
      local.get 10
      call 102
      ref.cast (ref null 11)
      local.set 6
      local.get 10
      call 102
      ref.cast (ref null 10)
      local.set 5
      local.get 10
      call 108
      local.set 4
      local.get 10
      call 102
      ref.cast (ref null 12)
      local.set 3
      local.get 10
      call 102
      ref.cast (ref null 11)
      local.set 2
      local.get 10
      call 102
      ref.cast (ref null 11)
      local.set 1
      local.get 10
      call 102
      ref.cast (ref null 22600)
      local.set 0
    else
      i32.const 0
      local.set 9
    end
    block ;; label = @1
      block ;; label = @2
        block (type 22682) (result (ref null 21855) (ref null 11)) ;; label = @3
          block ;; label = @4
            block (type 22164) (result (ref null 21236) (ref null 21048) (ref null 15)) ;; label = @5
              block ;; label = @6
                block (type 22682) (result (ref null 21855) (ref null 11)) ;; label = @7
                  block ;; label = @8
                    block (type 22164) (result (ref null 21236) (ref null 21048) (ref null 15)) ;; label = @9
                      block ;; label = @10
                        block (type 22682) (result (ref null 21855) (ref null 11)) ;; label = @11
                          block ;; label = @12
                            block (type 22164) (result (ref null 21236) (ref null 21048) (ref null 15)) ;; label = @13
                              block ;; label = @14
                                block ;; label = @15
                                  block (type 22682) (result (ref null 21855) (ref null 11)) ;; label = @16
                                    block ;; label = @17
                                      block (type 22164) (result (ref null 21236) (ref null 21048) (ref null 15)) ;; label = @18
                                        block ;; label = @19
                                          block (type 22682) (result (ref null 21855) (ref null 11)) ;; label = @20
                                            block ;; label = @21
                                              block (type 22164) (result (ref null 21236) (ref null 21048) (ref null 15)) ;; label = @22
                                                block ;; label = @23
                                                  block (type 22682) (result (ref null 21855) (ref null 11)) ;; label = @24
                                                    block ;; label = @25
                                                      block (type 22164) (result (ref null 21236) (ref null 21048) (ref null 15)) ;; label = @26
                                                        block ;; label = @27
                                                          block (result (ref null 18573)) ;; label = @28
                                                            block (type 21382) (result (ref null 11) i32 (ref null 27)) ;; label = @29
                                                              block ;; label = @30
                                                                block (result (ref null 0)) ;; label = @31
                                                                  block ;; label = @32
                                                                    block (result (ref null 0)) ;; label = @33
                                                                      block ;; label = @34
                                                                        block ;; label = @35
                                                                          block ;; label = @36
                                                                            local.get 9
                                                                            br_table 1 (;@35;) 2 (;@34;) 4 (;@32;) 6 (;@30;) 9 (;@27;) 11 (;@25;) 13 (;@23;) 15 (;@21;) 17 (;@19;) 19 (;@17;) 22 (;@14;) 24 (;@12;) 26 (;@10;) 28 (;@8;) 30 (;@6;) 32 (;@4;) 0 (;@36;)
                                                                          end
                                                                          unreachable
                                                                        end
                                                                        local.get 0
                                                                        struct.get 22600 46
                                                                        local.set 1
                                                                        global.get 1960
                                                                        br 1 (;@33;)
                                                                      end
                                                                      local.get 10
                                                                      call 106
                                                                      ref.cast (ref null 0)
                                                                    end
                                                                    local.set 11
                                                                    local.get 11
                                                                    ref.cast (ref null 0)
                                                                    i32.const 1
                                                                    local.set 9
                                                                    call_ref 0
                                                                    local.get 10
                                                                    call 104
                                                                    if ;; label = @33
                                                                      local.get 11
                                                                      ref.cast (ref null 0)
                                                                      local.get 10
                                                                      call 107
                                                                      br 32 (;@1;)
                                                                    end
                                                                    global.get 12305
                                                                    local.set 2
                                                                    block (result (ref null 11)) ;; label = @33
                                                                      local.get 1
                                                                      br_on_non_null 0 (;@33;)
                                                                      call 105
                                                                      throw 0
                                                                    end
                                                                    ref.cast (ref null 18645)
                                                                    struct.get 18645 3
                                                                    local.set 3
                                                                    block (result (ref null 11)) ;; label = @33
                                                                      local.get 2
                                                                      br_on_non_null 0 (;@33;)
                                                                      call 105
                                                                      throw 0
                                                                    end
                                                                    ref.cast (ref null 18350)
                                                                    struct.get 18350 2
                                                                    local.set 4
                                                                    block (result (ref null 12)) ;; label = @33
                                                                      local.get 3
                                                                      br_on_non_null 0 (;@33;)
                                                                      call 105
                                                                      throw 0
                                                                    end
                                                                    struct.get 12 2
                                                                    local.set 5
                                                                    block (result (ref null 18640)) ;; label = @33
                                                                      block (result (ref null 18640)) ;; label = @34
                                                                        block (result (ref null 20933)) ;; label = @35
                                                                          local.get 5
                                                                          block (result i32) ;; label = @36
                                                                            block ;; label = @37
                                                                              local.get 4
                                                                              i32.const 0
                                                                              i32.lt_s
                                                                              br_if 0 (;@37;)
                                                                              local.get 4
                                                                              local.get 4
                                                                              local.get 5
                                                                              array.len
                                                                              i32.lt_s
                                                                              br_if 1 (;@36;)
                                                                              drop
                                                                            end
                                                                            call 113
                                                                            throw 0
                                                                          end
                                                                          array.get 10
                                                                          ref.cast (ref null 20933)
                                                                          br_on_non_null 0 (;@35;)
                                                                          call 105
                                                                          throw 0
                                                                        end
                                                                        struct.get 20933 3
                                                                        br_on_cast 0 (;@34;) (ref null 11) (ref null 18640)
                                                                        call 110
                                                                        throw 0
                                                                      end
                                                                      br_on_non_null 0 (;@33;)
                                                                      call 105
                                                                      throw 0
                                                                    end
                                                                    struct.get 18640 2
                                                                    local.set 4
                                                                    global.get 8245
                                                                    br 1 (;@31;)
                                                                  end
                                                                  local.get 10
                                                                  call 106
                                                                  ref.cast (ref null 0)
                                                                end
                                                                local.set 11
                                                                local.get 11
                                                                ref.cast (ref null 0)
                                                                i32.const 2
                                                                local.set 9
                                                                call_ref 0
                                                                local.get 10
                                                                call 104
                                                                if ;; label = @31
                                                                  local.get 11
                                                                  ref.cast (ref null 0)
                                                                  local.get 10
                                                                  call 107
                                                                  br 30 (;@1;)
                                                                end
                                                                block (result (ref null 11)) ;; label = @31
                                                                  global.get 27337
                                                                  br_on_non_null 0 (;@31;)
                                                                  call 105
                                                                  throw 0
                                                                end
                                                                local.set 7
                                                                local.get 7
                                                                local.get 4
                                                                local.get 7
                                                                struct.get 11 0
                                                                ref.cast (ref 20603)
                                                                struct.get 20603 158
                                                                br 1 (;@29;)
                                                              end
                                                              ref.null 11
                                                              i32.const 0
                                                              local.get 10
                                                              call 106
                                                              ref.cast (ref null 27)
                                                            end
                                                            local.set 11
                                                            local.get 11
                                                            ref.cast (ref null 27)
                                                            i32.const 3
                                                            local.set 9
                                                            call_ref 27
                                                            local.get 10
                                                            call 104
                                                            if (type 16) (param (ref null 11)) (result (ref null 11)) ;; label = @29
                                                              drop
                                                              local.get 11
                                                              ref.cast (ref null 27)
                                                              local.get 10
                                                              call 107
                                                              br 28 (;@1;)
                                                            end
                                                            br_on_cast 0 (;@28;) (ref null 11) (ref null 18573)
                                                            call 110
                                                            throw 0
                                                          end
                                                          global.get 35540
                                                          ref.eq
                                                          i32.eqz
                                                          br_if 12 (;@15;)
                                                          local.get 0
                                                          struct.get 22600 149
                                                          local.set 2
                                                          local.get 0
                                                          struct.get 22600 167
                                                          local.set 1
                                                          block (result (ref null 11)) ;; label = @28
                                                            local.get 2
                                                            br_on_non_null 0 (;@28;)
                                                            call 105
                                                            throw 0
                                                          end
                                                          ref.cast (ref null 20821)
                                                          struct.get 20821 3
                                                          local.set 6
                                                          struct.new_default 21245
                                                          local.set 8
                                                          local.get 8
                                                          global.get 261
                                                          struct.set 21245 0
                                                          local.get 8
                                                          local.set 2
                                                          local.get 2
                                                          ref.cast (ref null 21236)
                                                          struct.new_default 21048
                                                          local.set 7
                                                          local.get 7
                                                          ref.cast (ref null 21048)
                                                          global.get 85
                                                          struct.set 21048 0
                                                          local.get 7
                                                          ref.cast (ref null 21048)
                                                          global.get 157
                                                          ref.cast (ref null 15)
                                                          br 1 (;@26;)
                                                        end
                                                        local.get 10
                                                        call 102
                                                        ref.cast (ref null 21236)
                                                        ref.null 21048
                                                        ref.null 15
                                                      end
                                                      i32.const 4
                                                      local.set 9
                                                      call 157
                                                      local.get 10
                                                      call 104
                                                      if (type 116576) (param (ref null 21236)) (result (ref null 21236)) ;; label = @26
                                                        local.get 10
                                                        call 103
                                                        br 25 (;@1;)
                                                      end
                                                      local.get 7
                                                      ref.cast (ref null 21048)
                                                      struct.set 21236 2
                                                      local.get 2
                                                      ref.cast (ref null 21245)
                                                      i32.const 4
                                                      struct.set 21245 4
                                                      local.get 2
                                                      ref.cast (ref null 21245)
                                                      local.get 1
                                                      ref.cast (ref null 21236)
                                                      struct.set 21245 3
                                                      block (result (ref null 21855)) ;; label = @26
                                                        local.get 6
                                                        ref.cast (ref null 21855)
                                                        br_on_non_null 0 (;@26;)
                                                        call 105
                                                        throw 0
                                                      end
                                                      local.get 2
                                                      br 1 (;@24;)
                                                    end
                                                    ref.null 21855
                                                    ref.null 11
                                                  end
                                                  i32.const 5
                                                  local.set 9
                                                  call 234
                                                  local.get 10
                                                  call 104
                                                  if (type 26808) (param i32) (result i32) ;; label = @24
                                                    drop
                                                    br 23 (;@1;)
                                                  end
                                                  drop
                                                  local.get 0
                                                  struct.get 22600 149
                                                  local.set 2
                                                  local.get 0
                                                  struct.get 22600 168
                                                  local.set 1
                                                  block (result (ref null 11)) ;; label = @24
                                                    local.get 2
                                                    br_on_non_null 0 (;@24;)
                                                    call 105
                                                    throw 0
                                                  end
                                                  ref.cast (ref null 20821)
                                                  struct.get 20821 3
                                                  local.set 6
                                                  struct.new_default 21245
                                                  local.set 8
                                                  local.get 8
                                                  global.get 261
                                                  struct.set 21245 0
                                                  local.get 8
                                                  local.set 2
                                                  local.get 2
                                                  ref.cast (ref null 21236)
                                                  struct.new_default 21048
                                                  local.set 7
                                                  local.get 7
                                                  ref.cast (ref null 21048)
                                                  global.get 85
                                                  struct.set 21048 0
                                                  local.get 7
                                                  ref.cast (ref null 21048)
                                                  global.get 157
                                                  ref.cast (ref null 15)
                                                  br 1 (;@22;)
                                                end
                                                local.get 10
                                                call 102
                                                ref.cast (ref null 21236)
                                                ref.null 21048
                                                ref.null 15
                                              end
                                              i32.const 6
                                              local.set 9
                                              call 157
                                              local.get 10
                                              call 104
                                              if (type 116576) (param (ref null 21236)) (result (ref null 21236)) ;; label = @22
                                                local.get 10
                                                call 103
                                                br 21 (;@1;)
                                              end
                                              local.get 7
                                              ref.cast (ref null 21048)
                                              struct.set 21236 2
                                              local.get 2
                                              ref.cast (ref null 21245)
                                              i32.const 4
                                              struct.set 21245 4
                                              local.get 2
                                              ref.cast (ref null 21245)
                                              local.get 1
                                              ref.cast (ref null 21236)
                                              struct.set 21245 3
                                              block (result (ref null 21855)) ;; label = @22
                                                local.get 6
                                                ref.cast (ref null 21855)
                                                br_on_non_null 0 (;@22;)
                                                call 105
                                                throw 0
                                              end
                                              local.get 2
                                              br 1 (;@20;)
                                            end
                                            ref.null 21855
                                            ref.null 11
                                          end
                                          i32.const 7
                                          local.set 9
                                          call 234
                                          local.get 10
                                          call 104
                                          if (type 26808) (param i32) (result i32) ;; label = @20
                                            drop
                                            br 19 (;@1;)
                                          end
                                          drop
                                          local.get 0
                                          struct.get 22600 149
                                          local.set 2
                                          local.get 0
                                          struct.get 22600 169
                                          local.set 1
                                          block (result (ref null 11)) ;; label = @20
                                            local.get 2
                                            br_on_non_null 0 (;@20;)
                                            call 105
                                            throw 0
                                          end
                                          ref.cast (ref null 20821)
                                          struct.get 20821 3
                                          local.set 6
                                          struct.new_default 21245
                                          local.set 8
                                          local.get 8
                                          global.get 261
                                          struct.set 21245 0
                                          local.get 8
                                          local.set 2
                                          local.get 2
                                          ref.cast (ref null 21236)
                                          struct.new_default 21048
                                          local.set 7
                                          local.get 7
                                          ref.cast (ref null 21048)
                                          global.get 85
                                          struct.set 21048 0
                                          local.get 7
                                          ref.cast (ref null 21048)
                                          global.get 157
                                          ref.cast (ref null 15)
                                          br 1 (;@18;)
                                        end
                                        local.get 10
                                        call 102
                                        ref.cast (ref null 21236)
                                        ref.null 21048
                                        ref.null 15
                                      end
                                      i32.const 8
                                      local.set 9
                                      call 157
                                      local.get 10
                                      call 104
                                      if (type 116576) (param (ref null 21236)) (result (ref null 21236)) ;; label = @18
                                        local.get 10
                                        call 103
                                        br 17 (;@1;)
                                      end
                                      local.get 7
                                      ref.cast (ref null 21048)
                                      struct.set 21236 2
                                      local.get 2
                                      ref.cast (ref null 21245)
                                      i32.const 6
                                      struct.set 21245 4
                                      local.get 2
                                      ref.cast (ref null 21245)
                                      local.get 1
                                      ref.cast (ref null 21236)
                                      struct.set 21245 3
                                      block (result (ref null 21855)) ;; label = @18
                                        local.get 6
                                        ref.cast (ref null 21855)
                                        br_on_non_null 0 (;@18;)
                                        call 105
                                        throw 0
                                      end
                                      local.get 2
                                      br 1 (;@16;)
                                    end
                                    ref.null 21855
                                    ref.null 11
                                  end
                                  i32.const 9
                                  local.set 9
                                  call 234
                                  local.get 10
                                  call 104
                                  if (type 26808) (param i32) (result i32) ;; label = @16
                                    drop
                                    br 15 (;@1;)
                                  end
                                  drop
                                  br 13 (;@2;)
                                end
                                local.get 0
                                struct.get 22600 149
                                local.set 2
                                local.get 0
                                struct.get 22600 169
                                local.set 1
                                block (result (ref null 11)) ;; label = @15
                                  local.get 2
                                  br_on_non_null 0 (;@15;)
                                  call 105
                                  throw 0
                                end
                                ref.cast (ref null 20821)
                                struct.get 20821 3
                                local.set 6
                                struct.new_default 21245
                                local.set 8
                                local.get 8
                                global.get 261
                                struct.set 21245 0
                                local.get 8
                                local.set 2
                                local.get 2
                                ref.cast (ref null 21236)
                                struct.new_default 21048
                                local.set 7
                                local.get 7
                                ref.cast (ref null 21048)
                                global.get 85
                                struct.set 21048 0
                                local.get 7
                                ref.cast (ref null 21048)
                                global.get 157
                                ref.cast (ref null 15)
                                br 1 (;@13;)
                              end
                              local.get 10
                              call 102
                              ref.cast (ref null 21236)
                              ref.null 21048
                              ref.null 15
                            end
                            i32.const 10
                            local.set 9
                            call 157
                            local.get 10
                            call 104
                            if (type 116576) (param (ref null 21236)) (result (ref null 21236)) ;; label = @13
                              local.get 10
                              call 103
                              br 12 (;@1;)
                            end
                            local.get 7
                            ref.cast (ref null 21048)
                            struct.set 21236 2
                            local.get 2
                            ref.cast (ref null 21245)
                            i32.const 4
                            struct.set 21245 4
                            local.get 2
                            ref.cast (ref null 21245)
                            local.get 1
                            ref.cast (ref null 21236)
                            struct.set 21245 3
                            block (result (ref null 21855)) ;; label = @13
                              local.get 6
                              ref.cast (ref null 21855)
                              br_on_non_null 0 (;@13;)
                              call 105
                              throw 0
                            end
                            local.get 2
                            br 1 (;@11;)
                          end
                          ref.null 21855
                          ref.null 11
                        end
                        i32.const 11
                        local.set 9
                        call 234
                        local.get 10
                        call 104
                        if (type 26808) (param i32) (result i32) ;; label = @11
                          drop
                          br 10 (;@1;)
                        end
                        drop
                        local.get 0
                        struct.get 22600 149
                        local.set 2
                        local.get 0
                        struct.get 22600 167
                        local.set 1
                        block (result (ref null 11)) ;; label = @11
                          local.get 2
                          br_on_non_null 0 (;@11;)
                          call 105
                          throw 0
                        end
                        ref.cast (ref null 20821)
                        struct.get 20821 3
                        local.set 6
                        struct.new_default 21245
                        local.set 8
                        local.get 8
                        global.get 261
                        struct.set 21245 0
                        local.get 8
                        local.set 2
                        local.get 2
                        ref.cast (ref null 21236)
                        struct.new_default 21048
                        local.set 7
                        local.get 7
                        ref.cast (ref null 21048)
                        global.get 85
                        struct.set 21048 0
                        local.get 7
                        ref.cast (ref null 21048)
                        global.get 157
                        ref.cast (ref null 15)
                        br 1 (;@9;)
                      end
                      local.get 10
                      call 102
                      ref.cast (ref null 21236)
                      ref.null 21048
                      ref.null 15
                    end
                    i32.const 12
                    local.set 9
                    call 157
                    local.get 10
                    call 104
                    if (type 116576) (param (ref null 21236)) (result (ref null 21236)) ;; label = @9
                      local.get 10
                      call 103
                      br 8 (;@1;)
                    end
                    local.get 7
                    ref.cast (ref null 21048)
                    struct.set 21236 2
                    local.get 2
                    ref.cast (ref null 21245)
                    i32.const 6
                    struct.set 21245 4
                    local.get 2
                    ref.cast (ref null 21245)
                    local.get 1
                    ref.cast (ref null 21236)
                    struct.set 21245 3
                    block (result (ref null 21855)) ;; label = @9
                      local.get 6
                      ref.cast (ref null 21855)
                      br_on_non_null 0 (;@9;)
                      call 105
                      throw 0
                    end
                    local.get 2
                    br 1 (;@7;)
                  end
                  ref.null 21855
                  ref.null 11
                end
                i32.const 13
                local.set 9
                call 234
                local.get 10
                call 104
                if (type 26808) (param i32) (result i32) ;; label = @7
                  drop
                  br 6 (;@1;)
                end
                drop
                local.get 0
                struct.get 22600 149
                local.set 2
                local.get 0
                struct.get 22600 168
                local.set 1
                block (result (ref null 11)) ;; label = @7
                  local.get 2
                  br_on_non_null 0 (;@7;)
                  call 105
                  throw 0
                end
                ref.cast (ref null 20821)
                struct.get 20821 3
                local.set 6
                struct.new_default 21245
                local.set 8
                local.get 8
                global.get 261
                struct.set 21245 0
                local.get 8
                local.set 2
                local.get 2
                ref.cast (ref null 21236)
                struct.new_default 21048
                local.set 7
                local.get 7
                ref.cast (ref null 21048)
                global.get 85
                struct.set 21048 0
                local.get 7
                ref.cast (ref null 21048)
                global.get 157
                ref.cast (ref null 15)
                br 1 (;@5;)
              end
              local.get 10
              call 102
              ref.cast (ref null 21236)
              ref.null 21048
              ref.null 15
            end
            i32.const 14
            local.set 9
            call 157
            local.get 10
            call 104
            if (type 116576) (param (ref null 21236)) (result (ref null 21236)) ;; label = @5
              local.get 10
              call 103
              br 4 (;@1;)
            end
            local.get 7
            ref.cast (ref null 21048)
            struct.set 21236 2
            local.get 2
            ref.cast (ref null 21245)
            i32.const 6
            struct.set 21245 4
            local.get 2
            ref.cast (ref null 21245)
            local.get 1
            ref.cast (ref null 21236)
            struct.set 21245 3
            block (result (ref null 21855)) ;; label = @5
              local.get 6
              ref.cast (ref null 21855)
              br_on_non_null 0 (;@5;)
              call 105
              throw 0
            end
            local.get 2
            br 1 (;@3;)
          end
          ref.null 21855
          ref.null 11
        end
        i32.const 15
        local.set 9
        call 234
        local.get 10
        call 104
        if (type 26808) (param i32) (result i32) ;; label = @3
          drop
          br 2 (;@1;)
        end
        drop
      end
      return
    end
    local.get 10
    call 104
    if ;; label = @1
      local.get 0
      local.get 10
      call 103
      local.get 1
      local.get 10
      call 103
      local.get 2
      local.get 10
      call 103
      local.get 3
      local.get 10
      call 103
      local.get 4
      local.get 10
      call 109
      local.get 5
      local.get 10
      call 103
      local.get 6
      local.get 10
      call 103
      local.get 7
      local.get 10
      call 103
      local.get 8
      local.get 10
      call 103
      local.get 9
      local.get 10
      call 109
    end
  )
