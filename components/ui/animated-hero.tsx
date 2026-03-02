"use client";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { MoveRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

function AnimatedHero() {
    const [titleNumber, setTitleNumber] = useState(0);
    const titles = useMemo(
        () => ["compliant", "controllable", "predictable", "trustworthy", "future-proof"],
        []
    );

    useEffect(() => {
        const timeoutId = setTimeout(() => {
            if (titleNumber === titles.length - 1) {
                setTitleNumber(0);
            } else {
                setTitleNumber(titleNumber + 1);
            }
        }, 2000);
        return () => clearTimeout(timeoutId);
    }, [titleNumber, titles]);

    return (
        <div className="w-full">
            <div className="container mx-auto">
                <div className="flex gap-8 py-12 lg:py-16 items-center justify-center flex-col">
                    <div className="flex gap-4 flex-col">
                        <h1 className="text-6xl md:text-8xl max-w-3xl tracking-tighter text-center font-bold text-[#3B2314] leading-[1.2]">
                            <span className="block mb-2">Stop guessing.</span>
                            <span className="text-[#A0522D] block mb-2">Make AI</span>
                            <span className="relative flex w-full justify-center overflow-hidden text-center md:pb-4 md:pt-1 text-[#E35336] min-h-[1.5em]">
                                <span className="opacity-0">future-proof</span>
                                {titles.map((title, index) => (
                                    <motion.span
                                        key={index}
                                        className="absolute font-semibold"
                                        initial={{ opacity: 0, y: -100 }}
                                        transition={{ type: "spring", stiffness: 50 }}
                                        animate={
                                            titleNumber === index
                                                ? {
                                                    y: 0,
                                                    opacity: 1,
                                                }
                                                : {
                                                    y: titleNumber > index ? -150 : 150,
                                                    opacity: 0,
                                                }
                                        }
                                    >
                                        {title}
                                    </motion.span>
                                ))}
                            </span>
                        </h1>

                        <p className="text-2xl md:text-4xl leading-relaxed tracking-tight text-[#8B6F5E] max-w-4xl text-center mx-auto mt-8 font-medium">
                            Get a <span className="text-[#A0522D] font-bold">compliance and security report</span> in minutes. Understand obligations under the EU AI Act before you deploy.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export { AnimatedHero };
